from __future__ import annotations

import itertools
import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from aistack.cli import sandbox as cli
from aistack.sandbox.declaration import SandboxDeclaration, SandboxRecipe, load_sandbox_declaration
from aistack.sandbox.run import LABEL, CommandResult, SandboxRun, cleanup, rto_minutes


class FakeDocker:
    """Answers what a WordPress restore asks Docker, and records it."""

    def __init__(self, *, home_status: str = "200", location: str = "", db_dies: bool = False) -> None:
        self.calls: list[list[str]] = []
        self.home_status = home_status
        self.location = location
        self.db_dies = db_dies

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        command = args[0]
        if command == "inspect" and "{{.Image}} {{.Config.Image}}" in args:
            return CommandResult(0, "sha256:db mariadb:11\n" if args[-1] == "wordpress_db" else "sha256:wp wordpress:latest\n")
        if command == "inspect":
            return CommandResult(0, "false\n" if self.db_dies else "true\n")
        if command == "logs":
            return CommandResult(0, "", "ERROR 1064 at line 12\n")
        if command == "run" and "tar" in args:
            target = Path(next(a for a in args if a.endswith(":/restore")).removesuffix(":/restore"))
            (target / "wp-content" / "uploads").mkdir(parents=True)
            (target / "wp-content" / "uploads" / "photo.jpg").write_text("x")
            return CommandResult(0)
        if command == "exec" and "php" in args:
            path = next(a for a in args if a.startswith("AISTACK_PATH=")).split("=", 1)[1]
            if path == "/wp-login.php":
                return CommandResult(0, "200\n\n4000\nlogin\n")
            return CommandResult(0, f"{self.home_status}\n{self.location}\n1234\n-\n")
        if command == "exec":
            query = args[-1]
            if "SELECT 1" in query:
                return CommandResult(1, "", "starting") if self.db_dies else CommandResult(0, "1\n")
            if "COUNT(*) FROM information_schema" in query:
                return CommandResult(0, "12\n")
            if "LIKE '%options'" in query:
                return CommandResult(0, "wp_options\n")
            if "option_name='siteurl'" in query or "option_name='home'" in query:
                return CommandResult(0, "https://www.example.org\n")
            return CommandResult(0, "3\n")
        if command == "ps":
            return CommandResult(0, "c1\nc2\n")
        if command == "network" and args[1] == "ls":
            return CommandResult(0, "n1\n")
        return CommandResult(0)


def _backups(tmp_path: Path, *, dump: bool = True) -> Path:
    directory = tmp_path / "backup"
    directory.mkdir()
    if dump:
        (directory / "db-20261007-0300.sql").write_text("old")
        (directory / "db-20261008-0300.sql").write_text("CREATE TABLE wp_options (x int);")
    (directory / "wp-content-20261008-0300.tar.gz").write_bytes(b"archive")
    return directory


def _declaration(tmp_path: Path, backup: Path, *, expansion: float = 4, margin_gib: float = 0) -> SandboxDeclaration:
    recipe = SandboxRecipe(
        name="wordpress", kind="wordpress_mariadb", backup_dir=backup,
        database_dump="db-*.sql", files_archive="wp-content-*.tar.gz",
        live_database_container="wordpress_db", live_web_container="wp_app",
        database_timeout_seconds=20, web_timeout_seconds=20,
    )
    return SandboxDeclaration(run_root=tmp_path / "sandbox", margin_gib=margin_gib, expansion=expansion,
                              recipes={"wordpress": recipe})


@pytest.fixture(autouse=True)
def _no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    ticks = itertools.count(0, 5)
    monkeypatch.setattr("aistack.sandbox.run.time.monotonic", lambda: float(next(ticks)))
    monkeypatch.setattr("aistack.sandbox.wordpress.time.sleep", lambda seconds: None)


def test_a_wordpress_backup_is_restored_checked_timed_and_removed(tmp_path: Path):
    docker = FakeDocker()
    run, report = cli.restore("wordpress", _declaration(tmp_path, _backups(tmp_path)), tmp_path / "data", docker)

    assert run.succeeded, run.failure
    assert run.recovery_seconds and run.recovery_seconds > 0
    assert run.facts["backup"]["database_dump"].endswith("db-20261008-0300.sql")
    assert run.facts["backup"]["same_night"] is True
    assert run.facts["database"]["table_prefix"] == "wp_"
    assert "status: success" in run.proposed_entry()
    assert "rto_minutes:" in run.proposed_entry()
    assert not run.directory.exists()
    assert run.steps[-1].name == "teardown" and run.steps[-1].ok
    assert json.loads(report.read_text())["result"] == "success"


def test_the_sandbox_is_isolated_and_reuses_the_live_images(tmp_path: Path):
    docker = FakeDocker()
    run, _ = cli.restore("wordpress", _declaration(tmp_path, _backups(tmp_path)), tmp_path / "data", docker)

    (create,) = [c for c in docker.calls if c[:2] == ["network", "create"]]
    assert "--internal" in create
    started = [c for c in docker.calls if c[0] == "run"]
    assert started
    for call in started:
        assert f"{LABEL}={run.run_id}" in call
        network = call[call.index("--network") + 1]
        assert network in (run.network, "none")
        assert not {"-p", "--publish", "-P", "--publish-all"} & set(call)
        assert "sha256:db" in call or "sha256:wp" in call
    # Live containers are only inspected, never exec'd into or stopped.
    live = {"wordpress_db", "wp_app"}
    for call in docker.calls:
        if live & set(call):
            assert call[0] == "inspect"


def test_the_throwaway_password_never_reaches_the_report(tmp_path: Path):
    run, report = cli.restore("wordpress", _declaration(tmp_path, _backups(tmp_path)), tmp_path / "data", FakeDocker())

    assert run.password not in report.read_text()
    assert run.password not in cli.summary(run)


def test_not_enough_room_stops_before_anything_starts(tmp_path: Path):
    docker = FakeDocker()
    run, report = cli.restore(
        "wordpress", _declaration(tmp_path, _backups(tmp_path), margin_gib=1e9), tmp_path / "data", docker
    )

    assert not run.succeeded
    assert run.failure.startswith("not enough room")
    assert not [c for c in docker.calls if c[0] == "run" or c[:2] == ["network", "create"]]
    assert not run.directory.exists()
    assert "status: failed" in run.proposed_entry()
    assert "rto_minutes" not in run.proposed_entry()
    assert json.loads(report.read_text())["result"] == "failed"


def test_a_missing_dump_is_named(tmp_path: Path):
    run, _ = cli.restore("wordpress", _declaration(tmp_path, _backups(tmp_path, dump=False)), tmp_path / "data", FakeDocker())

    assert "no database dump" in run.failure


def test_a_dump_that_does_not_load_fails_with_the_database_last_words(tmp_path: Path):
    run, _ = cli.restore(
        "wordpress", _declaration(tmp_path, _backups(tmp_path)), tmp_path / "data", FakeDocker(db_dies=True)
    )

    assert "stopped while loading" in run.failure and "ERROR 1064" in run.failure
    assert not run.directory.exists()


def test_a_wordpress_that_wants_to_be_installed_has_lost_its_tables(tmp_path: Path):
    docker = FakeDocker(home_status="302", location="https://www.example.org/wp-admin/install.php")
    run, _ = cli.restore("wordpress", _declaration(tmp_path, _backups(tmp_path)), tmp_path / "data", docker)

    assert not run.succeeded
    assert [c.name for c in run.checks if not c.ok] == ["home page"]


def test_a_redirect_to_its_own_address_is_a_working_site(tmp_path: Path):
    docker = FakeDocker(home_status="301", location="https://www.example.org/")
    run, _ = cli.restore("wordpress", _declaration(tmp_path, _backups(tmp_path)), tmp_path / "data", docker)

    assert run.succeeded


def test_recovery_time_rounds_to_the_nearest_minute_never_below_one():
    assert rto_minutes(37) == 1
    assert rto_minutes(190) == 3
    assert rto_minutes(150) == 3


def test_cleanup_removes_what_an_interrupted_run_left(tmp_path: Path):
    root = tmp_path / "sandbox"
    (root / "wordpress-20261008-120000" / "db").mkdir(parents=True)
    docker = FakeDocker()

    done = cleanup(root, docker)

    assert any(line.startswith("wordpress-20261008-120000: removed") for line in done)
    assert not (root / "wordpress-20261008-120000").exists()
    assert ["rm", "-f", "-v", "c1", "c2"] in docker.calls


def test_the_shipped_declaration_knows_wordpress():
    declaration = load_sandbox_declaration()

    recipe = declaration.recipes["wordpress"]
    assert recipe.live_web_container == "wp_app"
    assert str(declaration.run_root) == "/srv/aistack/sandbox"


def test_an_unknown_recipe_kind_is_named(tmp_path: Path):
    path = tmp_path / "sandbox.yml"
    path.write_text("run_root: /x\nrecipes:\n  foo:\n    kind: magic\n", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown kind `magic`"):
        load_sandbox_declaration(path)


def test_the_report_goes_where_the_data_lives(tmp_path: Path):
    assert cli.data_dir(tmp_path) == tmp_path / "reports" / "generated"
    (tmp_path / ".env").write_text("AISTACK_VERSION=dev\nAISTACK_DATA_DIR=./data\n", encoding="utf-8")
    assert cli.data_dir(tmp_path) == tmp_path / "data"


def test_the_command_lists_its_recipes(capsys: pytest.CaptureFixture[str]):
    assert cli.main(["recipes"]) == 0
    assert "wordpress" in capsys.readouterr().out


def test_a_run_has_its_own_names(tmp_path: Path):
    run = SandboxRun("wordpress", tmp_path)
    assert run.network.startswith("aistack-sandbox-wordpress-")
    assert run.name("db") == f"{run.network}-db"


def test_a_comparison_never_changes_the_verdict_or_the_recovery_time(tmp_path: Path):
    plain, _ = cli.restore("wordpress", _declaration(tmp_path, _backups(tmp_path)), tmp_path / "data", FakeDocker())
    other = tmp_path / "other"
    other.mkdir()
    compared, _ = cli.restore(
        "wordpress", _declaration(other, _backups(other)), other / "data", FakeDocker(), compare_live=True
    )

    assert compared.succeeded and plain.succeeded
    assert compared.recovery_seconds == plain.recovery_seconds
    assert set(compared.facts["comparison"]) == {"base", "wp-content"}
    assert [s.name for s in compared.steps][-2:] == ["compare with live", "teardown"]
