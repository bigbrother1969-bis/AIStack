from __future__ import annotations

import itertools
import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from aistack.cli import sandbox as cli
from aistack.sandbox.declaration import SandboxDeclaration, SandboxRecipe, load_sandbox_declaration
from aistack.sandbox.run import LABEL, CommandResult

GOOD = {
    "sessions": "ok", "explications": 120, "explications_unreadable": 0, "history_streams": 9,
    "declarations": 19, "environment_files": 3,
    "manifest": {"created": "2026-10-08T01:00:02Z", "host": "GIGABYTE", "commit": "d7a1f3a", "image_version": "dev"},
}


class FakeDocker:
    def __init__(self, *, inspected: dict | None = None, rebuild_fails: bool = False, web_dies: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.inspected = inspected if inspected is not None else GOOD
        self.rebuild_fails = rebuild_fails
        self.web_dies = web_dies

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        if args[0] == "inspect" and "{{.Image}} {{.Config.Image}}" in args:
            return CommandResult(0, "sha256:ai bigbrother1969/aistack-core:dev\n")
        if args[0] == "inspect":
            return CommandResult(0, "false\n" if self.web_dies else "true\n")
        if args[0] == "logs":
            return CommandResult(0, "", "ValueError: instance_config.yml declares no port for console\n")
        if args[0] == "run" and "aistack.cli.timemachine_rebuild" in args:
            if self.rebuild_fails:
                return CommandResult(1, "", "Traceback: broken history\n")
            data = Path(next(a for a in args if a.endswith(":/app/reports/generated")).split(":")[0])
            (data / "timemachine" / "graph").mkdir(parents=True)
            return CommandResult(0)
        if args[0] == "run" and "python" in args and "--entrypoint" in args:
            return CommandResult(0, json.dumps(self.inspected) + "\n")
        if args[0] == "exec":
            if self.web_dies:
                return CommandResult(1)
            path = next(a for a in args if a.startswith("AISTACK_PATH=")).split("=", 1)[1]
            return CommandResult(0, "200\n" if path == "/console.html" else "303\n")
        if args[0] == "ps":
            return CommandResult(0, "")
        if args[:2] == ["network", "ls"]:
            return CommandResult(0, "")
        return CommandResult(0)


def _declaration(tmp_path: Path) -> SandboxDeclaration:
    backup = tmp_path / "AIStack"
    backup.mkdir()
    (backup / "aistack-2026-10-07T01-00-02Z.tar.gz").write_bytes(b"old")
    (backup / "aistack-2026-10-08T01-00-02Z.tar.gz").write_bytes(b"archive")
    recipe = SandboxRecipe(
        name="aistack", kind="aistack_archive", backup_dir=backup, files_archive="aistack-*.tar.gz",
        live_web_container="aistack-web", web_timeout_seconds=20,
    )
    return SandboxDeclaration(run_root=tmp_path / "sandbox", margin_gib=0, expansion=4, recipes={"aistack": recipe})


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = itertools.count(0, 3)
    monkeypatch.setattr("aistack.sandbox.run.time.monotonic", lambda: float(next(ticks)))
    monkeypatch.setattr("aistack.sandbox.aistack_archive.time.sleep", lambda seconds: None)


def test_aistack_is_restored_its_graph_rebuilt_and_its_console_served(tmp_path: Path):
    run, report = cli.restore("aistack", _declaration(tmp_path), tmp_path / "data", FakeDocker())

    assert run.succeeded, run.failure
    assert run.facts["backup"]["files_archive"].endswith("aistack-2026-10-08T01-00-02Z.tar.gz")
    assert run.facts["archive"]["commit"] == "d7a1f3a"
    assert {check.name for check in run.checks if check.ok} >= {
        "archive manifest", "session database", "explications readable", "history restored",
        "declarations restored", "Time Machine graph rebuilt", "console",
    }
    assert "name: aistack" in run.proposed_entry() and "rto_minutes:" in run.proposed_entry()
    assert not run.directory.exists()
    assert json.loads(report.read_text())["result"] == "success"


def test_the_restored_secrets_are_never_given_to_a_sandbox_container(tmp_path: Path):
    docker = FakeDocker()
    run, _ = cli.restore("aistack", _declaration(tmp_path), tmp_path / "data", docker)

    for call in docker.calls:
        assert "--env-file" not in call
        assert not any(arg.split(":")[0].endswith("/env") for arg in call)
    for call in (c for c in docker.calls if c[0] == "run"):
        assert f"{LABEL}={run.run_id}" in call
        assert call[call.index("--network") + 1] in (run.network, "none")
        assert not {"-p", "--publish", "-P", "--publish-all"} & set(call)
        assert "/var/run/docker.sock" not in " ".join(call)


def test_a_damaged_session_database_fails_the_test(tmp_path: Path):
    damaged = {**GOOD, "sessions": "*** in database main ***"}
    run, _ = cli.restore("aistack", _declaration(tmp_path), tmp_path / "data", FakeDocker(inspected=damaged))

    assert not run.succeeded
    assert "session database" in [check.name for check in run.checks if not check.ok]


def test_a_graph_that_cannot_be_rebuilt_stops_the_run(tmp_path: Path):
    run, _ = cli.restore("aistack", _declaration(tmp_path), tmp_path / "data", FakeDocker(rebuild_fails=True))

    assert "broken history" in run.failure
    assert not run.directory.exists()


def test_a_web_application_that_stops_at_start_is_named(tmp_path: Path):
    run, _ = cli.restore("aistack", _declaration(tmp_path), tmp_path / "data", FakeDocker(web_dies=True))

    assert run.failure.startswith("AIStack stopped at start")


def test_the_shipped_declaration_knows_aistack():
    recipe = load_sandbox_declaration().recipes["aistack"]
    assert recipe.kind == "aistack_archive" and recipe.live_web_container == "aistack-web"


def test_a_wordpress_recipe_without_its_dump_is_named(tmp_path: Path):
    path = tmp_path / "sandbox.yml"
    path.write_text(
        "run_root: /x\nrecipes:\n  wp:\n    kind: wordpress_mariadb\n    backup_dir: /b\n"
        "    files_archive: a\n    live_web_container: w\n    live_database_container: d\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="`database_dump` is missing"):
        load_sandbox_declaration(path)
