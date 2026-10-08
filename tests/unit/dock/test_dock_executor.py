from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack.cli import dock as dock_cli
from aistack.dock import proposals as store
from aistack.dock.declaration import GovernedService
from aistack.dock.executor import Dock, compose_up, exclusive, keep_tag, recent_restore
from aistack.sandbox.declaration import SandboxDeclaration, SandboxRecipe
from aistack.sandbox.run import CommandResult

NOW = datetime(2026, 10, 9, 8, 0, tzinfo=timezone.utc)
OLD_ID, NEW_ID = "sha256:old-wp", "sha256:new-wp"
NEW_DIGEST = "sha256:" + "b" * 64
SERVICE = GovernedService("wordpress", "wordpress", ("wp_app", "wordpress_db"))
RECIPE = SandboxRecipe(
    name="wordpress", kind="wordpress_mariadb", backup_dir=Path("/backup"), database_dump="db-*.sql",
    files_archive="wp-*.tar.gz", live_database_container="wordpress_db", live_web_container="wp_app",
)
SANDBOX = SandboxDeclaration(run_root=Path("/srv/aistack/sandbox"), margin_gib=1, expansion=4, recipes={"wordpress": RECIPE})


class FakeDocker:
    """Containers run the image their compose tag pointed to when they
    were last recreated."""

    def __init__(self, *, watchtower: bool = False, healthy_after: bool = True, site: str = "200") -> None:
        self.calls: list[list[str]] = []
        self.tags = {"wordpress:latest": OLD_ID, "mariadb:11": "sha256:db"}
        self.running = {"wp_app": OLD_ID, "wordpress_db": "sha256:db"}
        self.restarts = {"wp_app": 0, "wordpress_db": 0}
        self.watchtower = watchtower
        self.healthy_after = healthy_after
        self.site = site

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        if args[0] == "inspect":
            name = args[-1]
            if "Labels" in args[2]:
                return CommandResult(0, f"{self.running[name]}|{'true' if self.watchtower else ''}")
            health = "unhealthy" if self.running[name] == NEW_ID and not self.healthy_after else ""
            return CommandResult(0, f"{self.running[name]}|running|{self.restarts[name]}|{health}")
        if args[0] == "pull":
            self.tags[args[1]] = NEW_ID
            return CommandResult(0)
        if args[:2] == ["image", "inspect"]:
            return CommandResult(0, self.tags[args[-1]] + "\n")
        if args[0] == "tag":
            source = args[1]
            self.tags[args[2]] = self.tags.get(source, source)
            return CommandResult(0)
        if args[0] == "compose":
            service = args[-1]
            container = "wp_app" if service == "wordpress" else "wordpress_db"
            image = "wordpress:latest" if container == "wp_app" else "mariadb:11"
            self.running[container] = self.tags[image]
            return CommandResult(0)
        if args[0] == "exec":
            if "sh" in args:
                return CommandResult(0, "12\n")
            path = next(item.split("=", 1)[1] for item in args if item.startswith("AISTACK_PATH="))
            if path == "/":
                site = self.site if self.running["wp_app"] == NEW_ID else "200"
                return CommandResult(0, f"{site}\n\n100\n-\n")
            return CommandResult(0, "200\n\n100\nlogin\n")
        raise AssertionError(f"unexpected docker {args}")


@dataclass
class FakeRun:
    run_id: str
    succeeded: bool = True
    failure: str = ""
    checks: list = field(default_factory=list)


class FakeRestorer:
    def __init__(self, *, fresh_fails: bool = False, rehearsal_fails: bool = False) -> None:
        self.calls: list[dict] = []
        self.fresh_fails = fresh_fails
        self.rehearsal_fails = rehearsal_fails

    def __call__(self, service, declaration, generated_dir, runner, progress=None, image_overrides=None):
        self.calls.append(image_overrides or {})
        fails = self.rehearsal_fails if image_overrides else self.fresh_fails
        run = FakeRun(f"wordpress-{len(self.calls)}", succeeded=not fails, failure="restore broke" if fails else "")
        return run, generated_dir / "sandbox" / f"{run.run_id}.json"


def _proposal(tmp_path: Path) -> store.Proposal:
    change = store.ImageChange(
        container="wp_app", image="wordpress:latest", from_digest="sha256:" + "a" * 64, to_digest=NEW_DIGEST,
        from_image_id=OLD_ID, compose_project="wordpress", compose_service="wordpress",
        compose_dir="/srv/wordpress", compose_files="/srv/wordpress/docker-compose.yml",
    )
    proposal = store.propose(tmp_path, "wordpress", [change], "WordPress security release", "alice", now=NOW)
    return store.validate(tmp_path, proposal.id, "alice", development=True)


def _dock(tmp_path: Path, docker: FakeDocker, restorer: FakeRestorer) -> Dock:
    return Dock(
        generated_dir=tmp_path, services=(SERVICE,), sandbox=SANDBOX, restorer=restorer, runner=docker,
        now=lambda: NOW, sleep=lambda seconds: None, settle_seconds=0,
    )


def _report(tmp_path: Path, started: datetime, result: str = "success", **facts) -> None:
    directory = tmp_path / "sandbox"
    directory.mkdir(parents=True, exist_ok=True)
    run_id = f"wordpress-{started:%Y%m%d-%H%M%S}"
    (directory / f"{run_id}.json").write_text(json.dumps({
        "run_id": run_id, "service": "wordpress", "started_at": started.isoformat(), "result": result, "facts": facts,
    }))


def _closing(proposal: store.Proposal) -> str:
    """The detail of the event that set the final state."""
    return next(h["detail"] for h in reversed(proposal.history) if h["event"] == proposal.status)


def _names(proposal: store.Proposal) -> list[tuple[str, str]]:
    return [(op["name"], op["status"]) for op in proposal.operations]


# -- the way through -----------------------------------------------------------

def test_a_validated_update_is_rehearsed_applied_and_checked(tmp_path: Path):
    docker, restorer = FakeDocker(), FakeRestorer()
    _proposal(tmp_path)
    _report(tmp_path, NOW - timedelta(hours=3))

    (done,) = _dock(tmp_path, docker, restorer).run_all()

    assert done.status == store.APPLIED
    assert _names(done) == [(name, "done") for name in (
        "preconditions", "sandbox restore", "fetch", "rehearsal", "keep", "apply", "live checks",
    )]
    # The recent restore served as the gate; only the rehearsal ran, with the new image by digest.
    assert restorer.calls == [{"wp_app": f"wordpress@{NEW_DIGEST}"}]
    assert ["pull", f"wordpress@{NEW_DIGEST}"] in docker.calls
    assert docker.running["wp_app"] == NEW_ID
    assert docker.tags[keep_tag(done.id, "wp_app")] == OLD_ID
    assert "login page HTTP 200" in done.operations[-1]["detail"]
    assert store.load(tmp_path, done.id).status == store.APPLIED


def test_the_container_is_recreated_with_its_own_compose_project():
    change = store.ImageChange("wp_app", "wordpress:latest", "a", "b", "id", "wordpress", "wordpress",
                               "/srv/wordpress", "/srv/wordpress/docker-compose.yml")
    assert compose_up(change) == [
        "compose", "-f", "/srv/wordpress/docker-compose.yml", "--project-directory", "/srv/wordpress",
        "-p", "wordpress", "up", "-d", "--no-deps", "--pull", "never", "wordpress",
    ]


def test_without_a_restore_of_the_last_24_hours_one_is_run_first(tmp_path: Path):
    docker, restorer = FakeDocker(), FakeRestorer()
    _proposal(tmp_path)
    _report(tmp_path, NOW - timedelta(hours=30))

    (done,) = _dock(tmp_path, docker, restorer).run_all()

    assert done.status == store.APPLIED
    assert restorer.calls == [{}, {"wp_app": f"wordpress@{NEW_DIGEST}"}]
    assert "run now" in done.operations[1]["detail"]


@pytest.mark.parametrize(("reports", "fresh"), [
    ([(3, "success", {})], True),
    ([(30, "success", {})], False),
    ([(2, "failed", {}), (5, "success", {})], False),
    ([(2, "success", {"rehearsed_with": {"wp_app": "x"}}), (5, "success", {})], True),
    ([(1, "success", {"rollback": {}})], False),
])
def test_the_newest_restore_with_the_live_images_decides(tmp_path: Path, reports, fresh):
    for hours, result, facts in reports:
        _report(tmp_path, NOW - timedelta(hours=hours), result, **facts)
    assert (recent_restore(tmp_path, "wordpress", NOW) is not None) is fresh


# -- stopping before the live service -------------------------------------------

def test_a_failed_restore_stops_with_nothing_touched(tmp_path: Path):
    docker, restorer = FakeDocker(), FakeRestorer(fresh_fails=True)
    _proposal(tmp_path)

    (done,) = _dock(tmp_path, docker, restorer).run_all()

    assert done.status == store.FAILED
    assert "nothing live was touched" in _closing(done)
    assert not any(call[0] in ("pull", "tag", "compose") for call in docker.calls)


def test_a_failed_rehearsal_stops_with_nothing_touched(tmp_path: Path):
    docker, restorer = FakeDocker(), FakeRestorer(rehearsal_fails=True)
    _proposal(tmp_path)
    _report(tmp_path, NOW - timedelta(hours=1))

    (done,) = _dock(tmp_path, docker, restorer).run_all()

    assert done.status == store.FAILED and _names(done)[-1] == ("rehearsal", "failed")
    assert docker.running["wp_app"] == OLD_ID
    assert not any(call[0] == "compose" for call in docker.calls)


def test_a_watchtower_label_stops_the_change(tmp_path: Path):
    _proposal(tmp_path)
    (done,) = _dock(tmp_path, FakeDocker(watchtower=True), FakeRestorer()).run_all()

    assert done.status == store.FAILED and "Watchtower" in _closing(done)


def test_a_container_changed_since_the_proposal_stops_the_change(tmp_path: Path):
    docker = FakeDocker()
    docker.running["wp_app"] = "sha256:something-else"
    _proposal(tmp_path)

    (done,) = _dock(tmp_path, docker, FakeRestorer()).run_all()

    assert done.status == store.FAILED and "propose again" in _closing(done)


# -- the way back ------------------------------------------------------------------

def test_failed_live_checks_put_the_previous_image_back(tmp_path: Path):
    docker, restorer = FakeDocker(healthy_after=False), FakeRestorer()
    _proposal(tmp_path)
    _report(tmp_path, NOW - timedelta(hours=1))

    (done,) = _dock(tmp_path, docker, restorer).run_all()

    assert done.status == store.ROLLED_BACK
    assert _names(done)[-3:] == [("live checks", "failed"), ("rollback", "done"), ("live checks after rollback", "done")]
    assert docker.running["wp_app"] == OLD_ID
    assert docker.tags["wordpress:latest"] == OLD_ID


def test_a_site_that_breaks_is_rolled_back(tmp_path: Path):
    docker = FakeDocker(site="500")
    _proposal(tmp_path)
    _report(tmp_path, NOW - timedelta(hours=1))

    (done,) = _dock(tmp_path, docker, FakeRestorer()).run_all()

    assert done.status == store.ROLLED_BACK and "HTTP 500" in _closing(done)


def test_an_interrupted_run_is_closed_and_says_what_it_may_have_left(tmp_path: Path):
    proposal = _proposal(tmp_path)
    proposal.status = store.RUNNING
    proposal.operations = [{"name": "apply", "status": "running"}]
    store.save(tmp_path, proposal)

    closed = _dock(tmp_path, FakeDocker(), FakeRestorer()).close_interrupted()

    assert closed == [proposal.id]
    reloaded = store.load(tmp_path, proposal.id)
    assert reloaded.status == store.FAILED and "check it" in reloaded.history[-1]["detail"]


def test_only_validated_proposals_are_taken(tmp_path: Path):
    change = store.ImageChange("wp_app", "wordpress:latest", "a", NEW_DIGEST, OLD_ID, "wordpress", "wordpress", "/srv/wordpress")
    store.propose(tmp_path, "wordpress", [change], "not yet validated by anyone", "alice")

    assert _dock(tmp_path, FakeDocker(), FakeRestorer()).run_all() == []


def test_one_executor_at_a_time(tmp_path: Path):
    with exclusive(tmp_path) as first, exclusive(tmp_path) as second:
        assert first and not second


def test_the_command_lists_and_shows(tmp_path: Path, capsys):
    proposal = _proposal(tmp_path)
    env = tmp_path / ".env"
    env.write_text(f"AISTACK_DATA_DIR={tmp_path}\n")

    assert dock_cli.main(["list"], root=tmp_path) == 0
    assert dock_cli.main(["show", proposal.id], root=tmp_path) == 0
    shown = capsys.readouterr().out
    assert "validated" in shown and "WordPress security release" in shown


# -- the transaction and the why -------------------------------------------------------

def test_the_change_runs_as_a_transaction_of_registered_kinds(tmp_path: Path):
    _proposal(tmp_path)
    _report(tmp_path, NOW - timedelta(hours=1))
    dock = _dock(tmp_path, FakeDocker(), FakeRestorer())

    (done,) = dock.run_all()

    assert [op["kind"] for op in done.operations] == [
        "dock.preconditions", "dock.sandbox_restore", "dock.fetch", "dock.rehearsal",
        "dock.keep", "dock.apply", "dock.live_checks",
    ]
    assert dock.transactions.registry.get("dock.rollback") is not None


def test_the_why_is_recorded_beside_the_container_s_observations(tmp_path: Path):
    from aistack.explications import read_latest_explication

    _proposal(tmp_path)
    _report(tmp_path, NOW - timedelta(hours=1))

    (done,) = _dock(tmp_path, FakeDocker(), FakeRestorer()).run_all()

    why = read_latest_explication("wordpress/wordpress", tmp_path / "explications")
    assert why is not None
    assert why.content.startswith("WordPress security release")
    assert "appliquée" in why.content
    assert why.source == "person:alice" and why.confidence == "Declared"
    assert why.metadata["dock_proposal"] == done.id and why.metadata["explication_status"] == "Validated"
    assert "validated_by" not in why.metadata  # alice validated her own proposal (development)
    assert done.history[-1]["event"] == "explication"


def test_a_change_stopped_before_the_live_service_records_its_why_too(tmp_path: Path):
    from aistack.explications import read_latest_explication

    _proposal(tmp_path)
    (done,) = _dock(tmp_path, FakeDocker(watchtower=True), FakeRestorer()).run_all()

    why = read_latest_explication("wordpress/wordpress", tmp_path / "explications")
    assert why is not None and "échouée" in why.content and "Watchtower" in why.content
