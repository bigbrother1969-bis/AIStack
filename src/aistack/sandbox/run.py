"""
One sandbox run (`ADR-0018` § 2, 3, 5): its names, its isolation, its
throwaway credentials, its steps and checks, its teardown, its report.

Every Docker call goes through a `Runner`, so the whole run can be
tested without Docker. Every container the run starts carries the
label `aistack.sandbox=<run id>`, joins the run's own `internal`
network or none, and publishes no port.
"""

from __future__ import annotations

import json
import math
import os
import secrets
import shutil
import subprocess
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LABEL = "aistack.sandbox"
PREFIX = "aistack-sandbox-"
HELPER_IMAGE_FILE = ".helper-image"


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


Runner = Callable[[Sequence[str], float], CommandResult]


def docker_runner(args: Sequence[str], timeout: float) -> CommandResult:
    """The real `docker` command."""

    try:
        done = subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return CommandResult(124, "", f"no answer within {timeout:g} s")
    except FileNotFoundError:
        return CommandResult(127, "", "the docker command is not installed")
    return CommandResult(done.returncode, done.stdout, done.stderr)


def host_runner(args: Sequence[str], timeout: float) -> CommandResult:
    """A command on the host itself (duplicity), not through Docker."""

    try:
        done = subprocess.run(list(args), capture_output=True, text=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return CommandResult(124, "", f"no answer within {timeout:g} s")
    except FileNotFoundError:
        return CommandResult(127, "", f"{args[0]} is not installed")
    return CommandResult(done.returncode, done.stdout, done.stderr)


class StepFailed(Exception):
    """A step that cannot go on; its message says why."""


@dataclass
class Step:
    name: str
    seconds: float
    ok: bool
    detail: str = ""


@dataclass
class Check:
    name: str
    ok: bool
    observed: str
    required: bool = True


@dataclass
class SandboxRun:
    service: str
    run_root: Path
    runner: Runner = docker_runner
    host: Runner = host_runner
    clock: Callable[[], float] = field(default=lambda: time.monotonic())
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    steps: list[Step] = field(default_factory=list)
    checks: list[Check] = field(default_factory=list)
    facts: dict[str, Any] = field(default_factory=dict)
    restore_started: float | None = None
    restore_finished: float | None = None
    failure: str = ""

    def __post_init__(self) -> None:
        self.run_id = f"{self.service}-{self.started_at:%Y%m%d-%H%M%S}"
        self.directory = self.run_root / self.run_id
        self.network = f"{PREFIX}{self.run_id}"
        # Throwaway, for this run only: never the live service's, never
        # written to the report.
        self.password = secrets.token_urlsafe(24)

    # -- names and isolation -------------------------------------------

    def name(self, role: str) -> str:
        return f"{PREFIX}{self.run_id}-{role}"

    def label_args(self) -> list[str]:
        return ["--label", f"{LABEL}={self.run_id}"]

    def hide(self, text: str) -> str:
        return text.replace(self.password, "***")

    def write_env(self, name: str, values: dict[str, str]) -> Path:
        """An env file only its owner reads, inside the run directory."""

        path = self.directory / name
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            for key, value in values.items():
                stream.write(f"{key}={value}\n")
        return path

    # -- docker ----------------------------------------------------------

    def docker_try(self, *args: str, timeout: float = 120) -> CommandResult:
        return self.runner(list(args), timeout)

    def docker(self, *args: str, timeout: float = 120) -> CommandResult:
        result = self.docker_try(*args, timeout=timeout)
        if result.returncode != 0:
            message = (result.stderr or result.stdout).strip().splitlines()
            raise StepFailed(self.hide(message[-1] if message else f"docker {args[0]} failed"))
        return result

    # -- steps and checks -----------------------------------------------

    @contextmanager
    def step(self, name: str) -> Iterator[None]:
        started = self.clock()
        try:
            yield
        except StepFailed as error:
            self.steps.append(Step(name, round(self.clock() - started, 1), False, self.hide(str(error))))
            raise
        except Exception as error:  # noqa: BLE001 - recorded, then raised as the run's failure
            detail = self.hide(f"{type(error).__name__}: {error}")
            self.steps.append(Step(name, round(self.clock() - started, 1), False, detail))
            raise StepFailed(detail) from error
        self.steps.append(Step(name, round(self.clock() - started, 1), True))

    def check(self, name: str, ok: bool, observed: str, *, required: bool = True) -> bool:
        self.checks.append(Check(name, ok, self.hide(observed), required))
        return ok

    def mark_restore_started(self) -> None:
        if self.restore_started is None:
            self.restore_started = self.clock()

    @property
    def succeeded(self) -> bool:
        return not self.failure and bool(self.checks) and all(c.ok for c in self.checks if c.required)

    @property
    def recovery_seconds(self) -> float | None:
        if self.restore_started is None or self.restore_finished is None:
            return None
        return round(self.restore_finished - self.restore_started, 1)

    # -- room ------------------------------------------------------------

    def check_room(self, files: Sequence[Path], expansion: float, margin_gib: float) -> None:
        needed = int(sum(path.stat().st_size for path in files) * expansion + margin_gib * 1024**3)
        where = self.run_root
        while not where.exists():
            where = where.parent
        free = shutil.disk_usage(where).free
        self.facts["room"] = {"needed_bytes": needed, "free_bytes": free, "where": str(where)}
        if free < needed:
            raise StepFailed(
                f"not enough room under {self.run_root}: {_gib(needed)} needed, {_gib(free)} free"
            )

    def make_directory(self, helper_image: str) -> None:
        self.directory.mkdir(parents=True, exist_ok=False)
        # What teardown, or a later cleanup, removes the root-owned
        # restored files with.
        (self.directory / HELPER_IMAGE_FILE).write_text(helper_image + "\n", encoding="utf-8")

    def create_network(self) -> None:
        self.docker("network", "create", "--internal", *self.label_args(), self.network)

    # -- teardown --------------------------------------------------------

    def teardown(self) -> None:
        """Containers, network, files: everything the run made, whatever
        happened before. Never raises; what it could not remove is noted."""

        started = self.clock()
        left = remove_run(self.run_id, self.directory, self.runner)
        self.steps.append(Step("teardown", round(self.clock() - started, 1), not left, "; ".join(left)))

    # -- report ----------------------------------------------------------

    def report(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "service": self.service,
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "result": "success" if self.succeeded else "failed",
            "failure": self.failure,
            "recovery_seconds": self.recovery_seconds,
            "facts": self.facts,
            "steps": [step.__dict__ for step in self.steps],
            "checks": [check.__dict__ for check in self.checks],
            "proposed_pra_entry": self.proposed_entry(),
        }

    def proposed_entry(self) -> str:
        """`pra_tests.yml`'s entry for this run — proposed, never written
        (`ADR-0018` § 5)."""

        lines = [
            f"  # Sandbox restore {self.run_id} (ADR-0018): "
            + ("every check passed" if self.succeeded else f"failed — {self.failure or 'a check failed'}"),
            f"  - name: {self.service}",
            "    last_test:",
            f"      status: {'success' if self.succeeded else 'failed'}",
            f'      date: "{self.started_at.date().isoformat()}"',
        ]
        seconds = self.recovery_seconds
        if self.succeeded and seconds is not None:
            lines.append(f"      rto_minutes: {rto_minutes(seconds)}")
        return "\n".join(lines)

    def write_report(self, generated_dir: Path) -> Path:
        target = generated_dir / "sandbox" / f"{self.run_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        text = self.hide(json.dumps(self.report(), indent=2, ensure_ascii=False))
        target.write_text(text + "\n", encoding="utf-8")
        return target


def _gib(size: float) -> str:
    return f"{size / 1024**3:.1f} GiB"


def rto_minutes(seconds: float) -> int:
    return max(1, math.floor(seconds / 60 + 0.5))


def remove_run(run_id: str, directory: Path, runner: Runner) -> list[str]:
    """Remove one run's containers, network and files. Returns what
    could not be removed."""

    left: list[str] = []
    listed = runner(["ps", "-aq", "--filter", f"label={LABEL}={run_id}"], 60)
    ids = listed.stdout.split()
    if ids and runner(["rm", "-f", "-v", *ids], 120).returncode != 0:
        left.append(f"containers {' '.join(ids)}")
    networks = runner(["network", "ls", "-q", "--filter", f"label={LABEL}={run_id}"], 60).stdout.split()
    if networks and runner(["network", "rm", *networks], 60).returncode != 0:
        left.append(f"network {' '.join(networks)}")
    if directory.exists():
        marker = directory / HELPER_IMAGE_FILE
        image = marker.read_text(encoding="utf-8").strip() if marker.is_file() else ""
        if image:
            # The restored files belong to the containers' users (root,
            # mysql, www-data): removed from inside a container, as root.
            runner(
                ["run", "--rm", "--network", "none", "--label", f"{LABEL}={run_id}",
                 "--entrypoint", "sh", "-v", f"{directory}:/run-dir", image,
                 "-c", "rm -rf /run-dir/* /run-dir/.[!.]* /run-dir/..?*"],
                300,
            )
        shutil.rmtree(directory, ignore_errors=True)
        if directory.exists():
            left.append(f"directory {directory}")
    return left


def cleanup(run_root: Path, runner: Runner) -> list[str]:
    """Every run an interruption may have left: by label, and by
    directory under `run_root`. Returns one line per run handled."""

    done: list[str] = []
    runs: set[str] = set()
    for kind in (["ps", "-a"], ["network", "ls"]):
        listed = runner([*kind, "--filter", f"label={LABEL}", "--format", f'{{{{.Label "{LABEL}"}}}}'], 60)
        runs.update(line.strip() for line in listed.stdout.splitlines() if line.strip())
    if run_root.is_dir():
        runs.update(path.name for path in run_root.iterdir() if path.is_dir())
    for run_id in sorted(runs):
        left = remove_run(run_id, run_root / run_id, runner)
        done.append(f"{run_id}: " + ("removed" if not left else "left " + "; ".join(left)))
    return done
