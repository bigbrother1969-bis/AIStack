from __future__ import annotations

import ast
import gzip
import json
from pathlib import Path

import pytest

from aistack import host_collector as hc

KEY = b"k" * 32


@pytest.fixture(autouse=True)
def _utc():
    """The logs' local times read as UTC — the zone put back after."""
    import os
    import time
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    yield
    if previous is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = previous
    time.tzset()


def _logs(root: Path) -> Path:
    logs = root / "log"
    (logs / "apt").mkdir(parents=True)
    with gzip.open(logs / "dpkg.log.2.gz", "wt") as stream:
        stream.write("2026-03-01 10:00:00 install foo:amd64 <none> 1.0\n")
    (logs / "dpkg.log.1").write_text(
        "2026-09-30 06:21:00 startup archives unpack\n"
        "2026-09-30 06:21:01 upgrade foo:amd64 1.0 1.1\n"
    )
    (logs / "dpkg.log").write_text("2026-10-08 06:51:00 remove bar:arm64 2.0 <none>\n")
    (logs / "apt" / "history.log").write_text(
        "\nStart-Date: 2026-10-08  06:50:58\n"
        "Commandline: apt-get -y upgrade\n"
        "Requested-By: pi (1000)\n"
        "Upgrade: foo:amd64 (1.0, 1.1), baz:amd64 (3, 4)\n"
        "Remove: bar:arm64 (2.0)\n"
        "End-Date: 2026-10-08  06:51:02\n"
    )
    return logs


def _tree(root: Path) -> Path:
    etc = root / "etc"
    (etc / "ssh").mkdir(parents=True)
    (etc / "ssh" / "sshd_config").write_text("Port 22\n")
    (etc / "adjtime").write_text("0.0\n")
    (etc / "hostname").write_text("raspberry\n")
    return etc


class Units:
    def __init__(self) -> None:
        self.states = {"ssh.service": "enabled", "aistack-backup.timer": "disabled"}

    def __call__(self, args):
        return "".join(f"{unit} {state} enabled\n" for unit, state in self.states.items())


def _run(root: Path, units: Units, now: str = "2026-10-08T19:00:00+00:00", **extra):
    return hc.collect(
        "raspberry", root / "out", KEY, watch=[str(root / "etc")], globs=[str(root / "srv" / "*" / "*.env")],
        ignore=[*hc.DEFAULT_IGNORE, f"{root}/etc/adjtime"], logs=root / "log", units=units, now=lambda: now, **extra,
    )


def _events(root: Path) -> list[dict]:
    return [json.loads(line) for line in (root / "out" / "events.jsonl").read_text().splitlines()]


def test_the_first_run_imports_every_rotation_and_records_a_baseline(tmp_path: Path):
    _logs(tmp_path)
    _tree(tmp_path)

    summary = _run(tmp_path, Units())

    events = _events(tmp_path)
    packages = [(e["at"], e["action"], e["package"], e["from"], e["to"]) for e in events if e["kind"] == "package"]
    assert packages == [
        ("2026-03-01T10:00:00+00:00", "install", "foo:amd64", None, "1.0"),
        ("2026-09-30T06:21:01+00:00", "upgrade", "foo:amd64", "1.0", "1.1"),
        ("2026-10-08T06:51:00+00:00", "remove", "bar:arm64", "2.0", None),
    ]
    (apt,) = [e for e in events if e["kind"] == "apt"]
    assert apt["commandline"] == "apt-get -y upgrade" and apt["requested_by"] == "pi (1000)"
    assert apt["counts"] == {"upgrade": 2, "remove": 1} and apt["ended"] == "2026-10-08T06:51:02+00:00"
    (baseline,) = [e for e in events if e["kind"] == "baseline"]
    assert baseline["files"] == 2 and baseline["units"] == 2
    assert not [e for e in events if e["kind"] in ("file", "unit")]
    assert summary["events"] == len(events)


def test_a_second_run_records_only_what_changed(tmp_path: Path):
    _logs(tmp_path)
    etc = _tree(tmp_path)
    units = Units()
    _run(tmp_path, units)
    first = len(_events(tmp_path))

    (etc / "ssh" / "sshd_config").write_text("Port 2222\n")
    (etc / "hostname").unlink()
    (etc / "cron.d").mkdir()
    (etc / "cron.d" / "backup").write_text("0 3 * * * root /usr/local/bin/backup\n")
    (etc / "adjtime").write_text("1.0\n")
    units.states["aistack-backup.timer"] = "enabled"
    with (tmp_path / "log" / "dpkg.log").open("a") as stream:
        stream.write("2026-10-08 20:00:00 install new:amd64 <none> 5\n")
    _run(tmp_path, units, now="2026-10-08T20:15:00+00:00")

    later = _events(tmp_path)[first:]
    files = {(e["action"], Path(e["path"]).name) for e in later if e["kind"] == "file"}
    assert files == {("modified", "sshd_config"), ("removed", "hostname"), ("added", "backup")}
    (unit,) = [e for e in later if e["kind"] == "unit"]
    assert (unit["unit"], unit["before"], unit["after"]) == ("aistack-backup.timer", "disabled", "enabled")
    assert [e["package"] for e in later if e["kind"] == "package"] == ["new:amd64"]
    assert not [e for e in later if e["kind"] == "apt"]


def test_nothing_changed_writes_no_event(tmp_path: Path):
    _logs(tmp_path)
    _tree(tmp_path)
    _run(tmp_path, Units())
    before = (tmp_path / "out" / "events.jsonl").read_text()

    assert _run(tmp_path, Units(), now="2026-10-08T19:15:00+00:00")["events"] == 0
    assert (tmp_path / "out" / "events.jsonl").read_text() == before


def test_a_file_is_known_by_a_keyed_fingerprint_never_its_content(tmp_path: Path):
    _logs(tmp_path)
    etc = _tree(tmp_path)
    secret = tmp_path / "srv" / "app"
    secret.mkdir(parents=True)
    (secret / "db.env").write_text("PASSWORD=hunter2\n")
    _run(tmp_path, Units())
    (secret / "db.env").write_text("PASSWORD=hunter3\n")
    _run(tmp_path, Units(), now="2026-10-08T19:15:00+00:00")

    written = "".join(p.read_text() for p in (tmp_path / "out").rglob("*.json*"))
    assert "hunter" not in written and "Port 22" not in written
    (change,) = [e for e in _events(tmp_path) if e["kind"] == "file"]
    assert change["before"]["fp"] != change["after"]["fp"]
    # Not a plain hash: without the key, the fingerprint cannot be recomputed.
    import hashlib
    assert hashlib.sha256(b"PASSWORD=hunter3\n").hexdigest()[:32] != change["after"]["fp"]
    assert etc.exists()


def test_a_file_root_alone_can_read_is_said_unreadable(tmp_path: Path, monkeypatch):
    _logs(tmp_path)
    _tree(tmp_path)
    monkeypatch.setattr(hc, "_fingerprint", lambda path, key: None)

    _run(tmp_path, Units())

    (baseline,) = [e for e in _events(tmp_path) if e["kind"] == "baseline"]
    assert baseline["unreadable"] == 2


def test_a_symbolic_link_is_recorded_by_its_target(tmp_path: Path):
    _logs(tmp_path)
    etc = _tree(tmp_path)
    (etc / "localtime").symlink_to("/usr/share/zoneinfo/Europe/Paris")
    _run(tmp_path, Units())
    (etc / "localtime").unlink()
    (etc / "localtime").symlink_to("/usr/share/zoneinfo/UTC")
    _run(tmp_path, Units(), now="2026-10-08T19:15:00+00:00")

    (change,) = [e for e in _events(tmp_path) if e["kind"] == "file"]
    assert change["after"]["link"] == "/usr/share/zoneinfo/UTC"


def test_systemctl_failing_is_said_not_taken_as_no_units(tmp_path: Path):
    _logs(tmp_path)
    _tree(tmp_path)
    _run(tmp_path, Units())

    def broken(args):
        raise OSError("System has not been booted with systemd")

    summary = _run(tmp_path, broken, now="2026-10-08T19:15:00+00:00")

    assert summary["problems"] == ["systemctl: System has not been booted with systemd"]
    assert not [e for e in _events(tmp_path) if e["kind"] == "unit"]


def test_the_key_is_drawn_once_and_kept_root_only(tmp_path: Path):
    key_path = tmp_path / "state" / "key"
    first = hc.load_key(key_path)

    assert len(first) == 32 and hc.load_key(key_path) == first
    assert oct(key_path.stat().st_mode & 0o777) == "0o600"


def test_the_declaration_adds_watches_and_ignores(tmp_path: Path):
    config = tmp_path / "collector.conf"
    config.write_text("# comment\nwatch = /home/pi/bin\nignore = /etc/cups/*  # noisy\nunknown = x\n")

    assert hc.read_config(config) == {"watch": ["/home/pi/bin"], "glob": [], "ignore": ["/etc/cups/*"]}


def test_the_default_globs_reach_compose_projects_one_and_two_levels_down():
    assert "/srv/*/docker-compose*.yml" in hc.DEFAULT_GLOBS
    assert "/srv/*/*/.env*" in hc.DEFAULT_GLOBS
    assert "/opt/*/compose*.yaml" in hc.DEFAULT_GLOBS


def test_the_collector_needs_nothing_but_the_standard_library():
    tree = ast.parse(Path(hc.__file__).read_text())
    imported = {
        (node.module if isinstance(node, ast.ImportFrom) else alias.name).split(".")[0]
        for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    import sys
    assert imported - {"__future__"} <= set(sys.stdlib_module_names)


def test_the_command_refuses_an_output_that_does_not_exist(tmp_path: Path, capsys):
    assert hc.main(["--host", "x", "--output", str(tmp_path / "missing"), "--key", str(tmp_path / "k")]) == 2
