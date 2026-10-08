"""
The dock executor (`ADR-0019` § 3–5): runs on the host, as the account
AIStack runs as, and takes the proposals an administrator validated —
one at a time, oldest first.

For each, in this order, every operation recorded in the proposal as it
happens (name, status, start, seconds, detail):

1. **preconditions** — the service is still declared, each container
   still runs the image the proposal was written against, carries no
   Watchtower label, and names its compose project;
2. **sandbox restore** — a restore of the service's latest backup has
   succeeded within the last 24 hours, else one is run now;
3. **fetch** — each new image is pulled by its registry digest, never
   by a tag that could have moved since the validation;
4. **rehearsal** — the same restore, with the new images;
5. **keep** — each previous image is tagged `aistack-dock/<container>:
   <proposal>`, so no clean-up removes the way back;
6. **apply** — the image's tag is moved to the new image and the
   container recreated with its own compose project
   (`docker compose up -d --no-deps --pull never <service>`);
7. **live checks** — every container of the service runs the expected
   image, is healthy and has not restarted after a settling time, and
   the recipe's own checks answer against the live service.

Any failure before *apply* stops the change with nothing live touched
(`failed`). A failure from *apply* on puts the previous images back the
same way and checks again (`rolled_back`); if that fails too the
proposal says so plainly (`failed`, the live service needs a person).

Docker is reached through a `Runner` and the sandbox through a
`restorer`, so the whole run is tested without either.
"""

from __future__ import annotations

import fcntl
import json
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aistack.dock import proposals as store
from aistack.dock.candidates import WATCHTOWER_LABEL
from aistack.dock.declaration import GovernedService
from aistack.dock.registry import parse_reference
from aistack.sandbox.compare import MARIADB
from aistack.sandbox.declaration import SandboxDeclaration, SandboxRecipe
from aistack.sandbox.run import Runner, docker_runner
from aistack.sandbox.wordpress import _FETCH

EXECUTOR = "dock"
FRESH = timedelta(hours=24)
KEEP_REPOSITORY = "aistack-dock"

# `restore(service, declaration, generated_dir, runner, ..., image_overrides=)`
# of `aistack.cli.sandbox`: returns the run and its report.
Restorer = Callable[..., tuple[Any, Path]]


class OperationFailed(Exception):
    """An operation that cannot go on; its message says why."""


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def keep_tag(proposal_id: str, container: str) -> str:
    """Where the previous image is kept: a repository of the dock's own,
    so no `image prune` of dangling images removes it."""

    return f"{KEEP_REPOSITORY}/{container.lower()}:{proposal_id}"


def pinned_reference(change: store.ImageChange) -> str:
    """`wordpress:latest` and `sha256:…` → `wordpress@sha256:…`."""

    return f"{parse_reference(change.image).short_repository}@{change.to_digest}"


def compose_up(change: store.ImageChange) -> list[str]:
    files = [item for item in change.compose_files.split(",") if item]
    if not files and change.compose_dir:
        files = [str(Path(change.compose_dir) / "docker-compose.yml")]
    args = ["compose"]
    for item in files:
        args += ["-f", item]
    if change.compose_dir:
        args += ["--project-directory", change.compose_dir]
    if change.compose_project:
        args += ["-p", change.compose_project]
    return [*args, "up", "-d", "--no-deps", "--pull", "never", change.compose_service]


def recent_restore(generated_dir: Path, recipe: str, now: datetime) -> dict[str, Any] | None:
    """The newest sandbox restore of `recipe` with the live images (not
    a rehearsal), when it succeeded and started within `FRESH` of `now`."""

    directory = generated_dir / "sandbox"
    for path in sorted(directory.glob(f"{recipe}-*.json"), reverse=True) if directory.is_dir() else []:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            started = datetime.fromisoformat(str(report.get("started_at")))
        except (OSError, ValueError, TypeError):
            continue
        facts = report.get("facts") or {}
        if report.get("service") != recipe or "rehearsed_with" in facts or "rollback" in facts:
            continue
        # The newest restore with the live images decides: a failure
        # after an older success means the backup no longer restores.
        if report.get("result") != "success":
            return None
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if now - started <= FRESH:
            return report
        return None
    return None


def _why_not(run: Any) -> str:
    if run.failure:
        return str(run.failure)
    failed = [f"{check.name}: {check.observed}" for check in run.checks if check.required and not check.ok]
    return "; ".join(failed) or "no check ran"


@dataclass
class Dock:
    generated_dir: Path
    services: tuple[GovernedService, ...]
    sandbox: SandboxDeclaration
    restorer: Restorer
    runner: Runner = docker_runner
    now: Callable[[], datetime] = field(default=lambda: datetime.now(timezone.utc))
    clock: Callable[[], float] = field(default=lambda: time.monotonic())
    sleep: Callable[[float], None] = field(default=lambda seconds: time.sleep(seconds))
    progress: Callable[[str], None] = field(default=lambda line: None)
    # After recreation: how long the containers must stay up without a
    # restart, and how long a health check may take to turn healthy.
    settle_seconds: float = 30
    health_timeout_seconds: float = 180

    # -- the queue -------------------------------------------------------

    def validated(self) -> list[store.Proposal]:
        found = [p for p in store.all_proposals(self.generated_dir) if p.status == store.VALIDATED]
        return sorted(found, key=lambda p: (p.decided_at, p.id))

    def close_interrupted(self) -> list[str]:
        """A proposal left `running` (the executor was stopped mid-way):
        closed as failed, saying the live state was not checked. Called
        with the lock held, so no other executor is at work on it."""

        closed = []
        for proposal in store.all_proposals(self.generated_dir):
            if proposal.status != store.RUNNING:
                continue
            last = proposal.operations[-1]["name"] if proposal.operations else "start"
            touched = any(op["name"] in ("apply", "rollback") for op in proposal.operations)
            detail = f"interrupted during `{last}`" + (
                ": the live service may run either image — check it" if touched else "; nothing live was touched"
            )
            self._finish(proposal, store.FAILED, detail)
            closed.append(proposal.id)
        return closed

    def run_all(self) -> list[store.Proposal]:
        done = []
        for proposal in self.validated():
            done.append(self.execute(proposal))
        return done

    # -- one proposal ----------------------------------------------------

    def _save(self, proposal: store.Proposal) -> None:
        store.save(self.generated_dir, proposal)

    def _finish(self, proposal: store.Proposal, status: str, detail: str) -> store.Proposal:
        proposal.status = status
        proposal.note(status, EXECUTOR, detail, _iso(self.now()))
        self._save(proposal)
        self.progress(f"{proposal.id}: {status}{' — ' + detail if detail else ''}")
        return proposal

    @contextmanager
    def operation(self, proposal: store.Proposal, name: str) -> Iterator[dict[str, Any]]:
        entry: dict[str, Any] = {
            "name": name, "status": "running", "started_at": _iso(self.now()), "seconds": 0.0, "detail": "",
        }
        proposal.operations.append(entry)
        self._save(proposal)
        self.progress(f"  … {name}")
        started = self.clock()
        try:
            yield entry
        except OperationFailed as error:
            entry["status"], entry["detail"] = "failed", str(error)
            raise
        except Exception as error:  # noqa: BLE001 - recorded, then the change stops on it
            entry["status"], entry["detail"] = "failed", f"{type(error).__name__}: {error}"
            raise OperationFailed(entry["detail"]) from error
        else:
            entry["status"] = "done"
        finally:
            entry["seconds"] = round(self.clock() - started, 1)
            self._save(proposal)

    def docker(self, *args: str, timeout: float = 120) -> str:
        result = self.runner(list(args), timeout)
        if result.returncode != 0:
            lines = (result.stderr or result.stdout).strip().splitlines()
            raise OperationFailed(f"docker {' '.join(args[:2])}: {lines[-1] if lines else 'failed'}")
        return result.stdout.strip()

    def execute(self, proposal: store.Proposal) -> store.Proposal:
        # Read again: it may have been rejected since the queue was read.
        proposal = store.load(self.generated_dir, proposal.id)
        if proposal.status != store.VALIDATED:
            return proposal
        proposal.status = store.RUNNING
        proposal.note(store.RUNNING, EXECUTOR, at=_iso(self.now()))
        self._save(proposal)
        self.progress(f"{proposal.id}: {proposal.service}, {len(proposal.changes)} image(s)")

        service = next((s for s in self.services if s.name == proposal.service), None)
        recipe = self.sandbox.recipes.get(service.recipe) if service else None
        new_images: dict[str, str] = {}
        try:
            with self.operation(proposal, "preconditions") as entry:
                if service is None or recipe is None:
                    raise OperationFailed(
                        f"`{proposal.service}` is no longer declared in dock.yml with a sandbox recipe"
                    )
                entry["detail"] = self._preconditions(proposal, service)
            with self.operation(proposal, "sandbox restore") as entry:
                entry["detail"] = self._restore_gate(recipe)
            with self.operation(proposal, "fetch") as entry:
                for change in proposal.changes:
                    reference = pinned_reference(change)
                    self.docker("pull", reference, timeout=1800)
                    new_images[change.container] = self.docker("image", "inspect", "--format", "{{.Id}}", reference)
                entry["detail"] = ", ".join(pinned_reference(change) for change in proposal.changes)
            with self.operation(proposal, "rehearsal") as entry:
                overrides = {change.container: pinned_reference(change) for change in proposal.changes}
                run, report = self.restorer(
                    recipe.name, self.sandbox, self.generated_dir, self.runner,
                    progress=self.progress, image_overrides=overrides,
                )
                if not run.succeeded:
                    raise OperationFailed(f"{run.run_id}: {_why_not(run)}")
                entry["detail"] = f"{run.run_id} — {report.name}"
            with self.operation(proposal, "keep") as entry:
                for change in proposal.changes:
                    self.docker("tag", change.from_image_id, keep_tag(proposal.id, change.container))
                entry["detail"] = ", ".join(keep_tag(proposal.id, c.container) for c in proposal.changes)
        except OperationFailed as error:
            return self._finish(proposal, store.FAILED, f"{error} — nothing live was touched")

        applied: list[store.ImageChange] = []
        try:
            with self.operation(proposal, "apply") as entry:
                for change in proposal.changes:
                    applied.append(change)
                    self.docker("tag", pinned_reference(change), change.image)
                    self.docker(*compose_up(change), timeout=600)
                entry["detail"] = ", ".join(f"{c.container} → {c.to_digest[:19]}…" for c in proposal.changes)
            with self.operation(proposal, "live checks") as entry:
                entry["detail"] = self.live_checks(service, recipe, new_images)
        except OperationFailed as error:
            return self._roll_back(proposal, service, recipe, applied, str(error))
        return self._finish(proposal, store.APPLIED, "")

    def _roll_back(
        self,
        proposal: store.Proposal,
        service: GovernedService | None,
        recipe: SandboxRecipe | None,
        applied: list[store.ImageChange],
        reason: str,
    ) -> store.Proposal:
        assert service is not None and recipe is not None
        try:
            with self.operation(proposal, "rollback") as entry:
                for change in reversed(applied):
                    self.docker("tag", keep_tag(proposal.id, change.container), change.image)
                    self.docker(*compose_up(change), timeout=600)
                entry["detail"] = ", ".join(c.container for c in applied)
            with self.operation(proposal, "live checks after rollback") as entry:
                entry["detail"] = self.live_checks(
                    service, recipe, {change.container: change.from_image_id for change in applied}
                )
        except OperationFailed as error:
            return self._finish(
                proposal, store.FAILED,
                f"{reason}; the way back failed too ({error}) — the live service needs a person",
            )
        return self._finish(proposal, store.ROLLED_BACK, f"{reason} — the previous images run again")

    # -- the gates ---------------------------------------------------------

    def _preconditions(self, proposal: store.Proposal, service: GovernedService) -> str:
        if not proposal.changes:
            raise OperationFailed("the proposal names no image")
        for change in proposal.changes:
            if change.container not in service.containers:
                raise OperationFailed(f"{change.container} is not a container of `{service.name}` in dock.yml")
            if not change.compose_service or not (change.compose_dir or change.compose_files):
                raise OperationFailed(f"{change.container} names no compose project: the dock cannot recreate it")
            if not change.from_image_id or not change.to_digest:
                raise OperationFailed(f"{change.container}: the proposal lacks the image it replaces or the new digest")
            shown = self.docker(
                "inspect", "--format",
                f'{{{{.Image}}}}|{{{{index .Config.Labels "{WATCHTOWER_LABEL}"}}}}', change.container,
            ).split("|")
            if shown[0] != change.from_image_id:
                raise OperationFailed(
                    f"{change.container} no longer runs the image the proposal was written against — propose again"
                )
            if shown[1:2] and shown[1].lower() == "true":
                raise OperationFailed(
                    f"{change.container} still carries Watchtower's label: remove it from its compose file, "
                    "then propose again"
                )
        return ", ".join(change.container for change in proposal.changes)

    def _restore_gate(self, recipe: SandboxRecipe) -> str:
        found = recent_restore(self.generated_dir, recipe.name, self.now())
        if found is not None:
            return f"{found.get('run_id')} (success, {found.get('started_at')}), less than 24 h old"
        run, report = self.restorer(recipe.name, self.sandbox, self.generated_dir, self.runner, progress=self.progress)
        if not run.succeeded:
            raise OperationFailed(f"the latest backup does not restore: {run.run_id}: {_why_not(run)}")
        return f"{run.run_id} — run now, success — {report.name}"

    # -- the live service --------------------------------------------------

    def _state(self, container: str) -> tuple[str, str, int, str]:
        shown = self.docker(
            "inspect", "--format",
            "{{.Image}}|{{.State.Status}}|{{.RestartCount}}|{{if .State.Health}}{{.State.Health.Status}}{{end}}",
            container,
        ).split("|")
        shown += [""] * (4 - len(shown))
        try:
            restarts = int(shown[2] or 0)
        except ValueError:
            restarts = 0
        return shown[0], shown[1], restarts, shown[3]

    def live_checks(self, service: GovernedService, recipe: SandboxRecipe, expected: dict[str, str]) -> str:
        """Every container of the service: the expected image, running,
        healthy, and still so after `settle_seconds` with no restart;
        then the recipe's own checks against the live service."""

        deadline = self.clock() + self.health_timeout_seconds
        restarts: dict[str, int] = {}
        for container in service.containers:
            while True:
                image, status, count, health = self._state(container)
                if container in expected and image != expected[container]:
                    raise OperationFailed(f"{container} runs {image[:19]}…, not the expected {expected[container][:19]}…")
                if health == "unhealthy":
                    raise OperationFailed(f"{container} is unhealthy")
                if status == "running" and health in ("", "healthy"):
                    restarts[container] = count
                    break
                if self.clock() > deadline:
                    raise OperationFailed(
                        f"{container} is {status}{' (' + health + ')' if health else ''} "
                        f"after {self.health_timeout_seconds:g} s"
                    )
                self.sleep(5)
        self.sleep(self.settle_seconds)
        for container in service.containers:
            _, status, count, health = self._state(container)
            if status != "running" or count != restarts[container] or health == "unhealthy":
                raise OperationFailed(f"{container} did not stay up ({status}, {count - restarts[container]} restart(s))")
        said = [f"{len(service.containers)} container(s) up {self.settle_seconds:g} s without restart"]
        said += self._recipe_checks(recipe)
        return "; ".join(said)

    def _recipe_checks(self, recipe: SandboxRecipe) -> list[str]:
        if recipe.kind != "wordpress_mariadb":
            return []
        answer = self.docker(
            "exec", recipe.live_database_container, "sh", "-c", MARIADB, "sh", "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema=DATABASE()", timeout=60,
        )
        if not answer.isdigit() or int(answer) == 0:
            raise OperationFailed(f"the live database answers no table ({answer or 'nothing'})")

        def fetch(path: str) -> list[str]:
            result = self.runner(
                ["exec", "-e", f"AISTACK_PATH={path}", "-e", "AISTACK_HOST=localhost",
                 recipe.live_web_container, "php", "-r", _FETCH], 60,
            )
            return result.stdout.splitlines() if result.returncode == 0 else []

        home = fetch("/")
        status, location = (home + ["", ""])[:2]
        if not (status == "200" or (status.startswith("3") and "install.php" not in location)):
            raise OperationFailed(f"the live site answers HTTP {status or 'nothing'}{' → ' + location if location else ''}")
        login = fetch("/wp-login.php")
        if not login or login[0] != "200" or login[3:4] != ["login"]:
            raise OperationFailed(f"the live login page answers {('HTTP ' + login[0]) if login else 'nothing'}")
        return [f"database: {answer} table(s)", f"home page HTTP {status}", "login page HTTP 200"]


@contextmanager
def exclusive(generated_dir: Path) -> Iterator[bool]:
    """One executor at a time: yields False when another holds the lock."""

    path = generated_dir / "dock" / "executor.lock"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)
