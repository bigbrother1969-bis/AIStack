"""The host unit of the boot facts and the reader of its file (ADR-0032, B1)."""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack import boot_facts as unit
from aistack.boot_checks.facts import FACTS, Container, parse_facts, read_facts_file

NOW = datetime(2026, 11, 26, 9, 30, tzinfo=timezone.utc)

MOUNTINFO = "\n".join(
    [
        "22 1 8:2 / / rw,relatime shared:1 - ext4 /dev/sda2 rw",
        "23 22 0:21 / /proc rw shared:5 - proc proc rw",
        "24 22 0:22 / /sys rw shared:6 - sysfs sysfs rw",
        "25 22 0:5 / /dev rw shared:2 - devtmpfs udev rw",
        "26 22 8:3 / /srv rw shared:9 - ext4 /dev/sda3 rw",
        "27 22 0:60 / /var/lib/docker/overlay2/x/merged rw - overlay overlay rw",
        "28 22 0:61 / /mnt/My\\040Share rw - cifs //nas/share rw",
        "29 22 0:30 / /run rw - tmpfs tmpfs rw",
        "not a mount line",
    ]
)
DOCKER = (
    "paperless\trunning\tUp 2 hours (healthy)\n"
    "immich\trunning\tUp 2 hours (unhealthy)\n"
    "kuma\trunning\tUp 3 minutes (health: starting)\n"
    "olala\texited\tExited (0) 3 days ago\n"
    "plain\trunning\tUp 2 hours\n"
    "\n"
    "broken line\n"
)


def test_the_start_is_the_time_less_the_uptime_never_the_journal() -> None:
    facts = unit.boot_facts(NOW, "25200.77 99999.0\n", "abc-123\n")

    assert facts == {"booted_at": "2026-11-26T02:30:00+00:00", "uptime_seconds": 25200, "boot_id": "abc-123"}


def test_failed_units_are_names_only_and_a_clean_host_has_none() -> None:
    text = "foo.service loaded failed failed Foo thing\nbar.mount loaded failed failed Bar\nfoo.service loaded failed failed again\n"

    assert unit.failed_units(text) == ["bar.mount", "foo.service"]
    assert unit.failed_units("") == []


def test_only_real_file_systems_are_mounted_places_and_escapes_are_read() -> None:
    assert unit.mounted(MOUNTINFO) == ["/", "/mnt/My Share", "/srv"]


def test_what_a_sandbox_or_the_kernel_adds_is_not_a_mounted_place() -> None:
    text = "\n".join(
        [
            "22 1 8:2 / / rw - ext4 /dev/sda2 rw",
            "30 22 0:50 / /proc/fs/nfsd rw - nfsd nfsd rw",
            "31 22 0:51 / /run/user/1000/gvfs rw - fuse.gvfsd-fuse gvfsd-fuse rw",
        ]
    )

    assert unit.mounted(text) == ["/"]


def test_the_mounts_are_the_hosts_and_the_units_own_view_is_only_the_fallback(tmp_path: Path) -> None:
    proc = _proc(tmp_path)
    (proc / "1").mkdir()
    (proc / "1/mountinfo").write_text("22 1 8:2 / /srv rw - ext4 /dev/sda3 rw\n", encoding="utf-8")

    assert unit.mounted(unit._host_mountinfo(proc)) == ["/srv"]

    (proc / "1/mountinfo").unlink()

    assert "/mnt/My Share" in unit.mounted(unit._host_mountinfo(proc))


def test_a_container_has_its_state_and_its_health() -> None:
    found = {item["name"]: (item["state"], item["health"]) for item in unit.containers(DOCKER)}

    assert found == {
        "paperless": ("running", "healthy"),
        "immich": ("running", "unhealthy"),
        "kuma": ("running", "starting"),
        "olala": ("exited", "none"),
        "plain": ("running", "none"),
    }


def test_the_rules_of_docker_user_are_counted_and_the_chain_line_is_not() -> None:
    text = "-N DOCKER-USER\n-A DOCKER-USER -s 1.2.3.4/32 -j DROP\n-A DOCKER-USER -j RETURN\n"

    assert unit.docker_user_rules(text) == 2


def test_the_previous_run_ended_cleanly_only_if_its_journal_says_it_was_shut_down() -> None:
    clean = ["x", "Reached target Power-Off.", "Shutting down."]
    brutal = ["x", "kernel: something", "NetworkManager: still running"]

    assert unit.previous_boot_ended_cleanly("\n".join(clean))
    assert not unit.previous_boot_ended_cleanly("\n".join(brutal))


def test_the_ups_status_is_read_from_its_own_line_and_nothing_else() -> None:
    assert unit.ups_status("battery.charge: 100\nups.status: OL\nups.load: 10\n") == "OL"

    with pytest.raises(OSError):
        unit.ups_status("battery.charge: 100\n")


def test_a_probe_is_written_under_its_label_never_its_url() -> None:
    assert unit.parse_probes(["proxy=http://127.0.0.1:80/, web=https://example.org/x"]) == {
        "proxy": "http://127.0.0.1:80/",
        "web": "https://example.org/x",
    }

    for bad in ("proxy", "proxy=ftp://x", "=http://x"):
        with pytest.raises(ValueError):
            unit.parse_probes([bad])


def _proc(tmp_path: Path) -> Path:
    proc = tmp_path / "proc"
    (proc / "sys/kernel/random").mkdir(parents=True)
    (proc / "self").mkdir()
    (proc / "uptime").write_text("600.5 1.0\n", encoding="utf-8")
    (proc / "sys/kernel/random/boot_id").write_text("boot-1\n", encoding="utf-8")
    (proc / "self/mountinfo").write_text(MOUNTINFO, encoding="utf-8")
    (proc / "modules").write_text("kvm_intel 1 0 - Live 0x0\nvfat 1 0 - Live 0x0\n", encoding="utf-8")

    return proc


def _answers(monkeypatch, **fail: str) -> None:
    texts = {
        "failed_units": "",
        "containers": DOCKER,
        "docker_user": "-A DOCKER-USER -j RETURN\n",
        "previous_boot": "Reached target Power-Off.\n",
        "ups": "ups.status: OL\n",
        "clock": "yes\n",
        "throttled": "throttled=0x50005\n",
    }

    def run(name: str, ups: str = "") -> str:
        if name in fail:
            raise OSError(fail[name])

        return texts[name]

    monkeypatch.setattr(unit, "_run", run)


def test_every_source_is_read_and_the_file_holds_facts_only(tmp_path: Path, monkeypatch) -> None:
    _answers(monkeypatch)
    report = unit.collect(NOW, {"proxy": "http://127.0.0.1:80/"}, "apc@localhost", proc=_proc(tmp_path), probe_one=lambda url: 200)

    assert report["sources"] == {
        "boot": "ok", "failed_units": "ok", "mounts": "ok", "containers": "ok", "docker_user_rules": "ok",
        "kvm_modules": "ok", "previous_boot_clean": "ok", "clock_synced": "ok", "throttled": "absent",
        "ups": "ok", "probes": "ok",
    }
    assert report["probes"] == {"proxy": 200}
    assert report["kvm_modules"] is True and report["ups"] == "OL" and report["failed_units"] == []
    assert "127.0.0.1" not in json.dumps(report) and "http" not in json.dumps(report)


def test_a_source_that_fails_says_so_and_does_not_stop_the_others(tmp_path: Path, monkeypatch) -> None:
    _answers(monkeypatch, containers="Cannot connect to the Docker daemon")
    report = unit.collect(NOW, {}, "", proc=_proc(tmp_path))

    assert report["sources"]["containers"] == "error: Cannot connect to the Docker daemon"
    assert report["sources"]["ups"] == "absent" and report["sources"]["probes"] == "absent"
    assert "containers" not in report and report["failed_units"] == []


def test_the_commands_are_a_closed_list_run_without_a_shell(monkeypatch) -> None:
    seen: list[list[str]] = []

    def run(command, **kwargs):
        seen.append(command)
        assert kwargs.get("shell") is not True

        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(unit.subprocess, "run", run)
    monkeypatch.setattr(unit.shutil, "which", lambda name: f"/usr/bin/{name}")

    for name in unit.COMMANDS:
        unit._run(name, "apc@localhost")

    assert [command[0] for command in seen] == ["systemctl", "docker", "iptables", "journalctl", "upsc", "vcgencmd", "timedatectl"]
    assert seen[4] == ["upsc", "apc@localhost"]

    with pytest.raises(KeyError):
        unit._run("rm")


def test_a_command_that_fails_or_is_missing_is_an_error_not_an_empty_answer(monkeypatch) -> None:
    monkeypatch.setattr(unit.shutil, "which", lambda name: None)

    with pytest.raises(OSError, match="not found"):
        unit._run("containers")

    monkeypatch.setattr(unit.shutil, "which", lambda name: name)
    monkeypatch.setattr(
        unit.subprocess, "run", lambda command, **_: subprocess.CompletedProcess(command, 1, stdout="", stderr="denied\n")
    )

    with pytest.raises(OSError, match="denied"):
        unit._run("containers")


def test_the_unit_writes_the_file_as_the_owner_of_its_directory(tmp_path: Path, monkeypatch) -> None:
    _answers(monkeypatch)
    monkeypatch.setattr(unit.os, "chown", lambda *_: None)
    monkeypatch.setattr(unit, "collect", lambda now, probes, ups: {"collected_at": now.isoformat(), "sources": {}})
    monkeypatch.setattr(sys, "argv", ["aistack-boot-facts", "--output", str(tmp_path / "out")])

    assert unit.main() == 0
    assert "collected_at" in json.loads((tmp_path / "out" / unit.OUTPUT_NAME).read_text(encoding="utf-8"))


def test_a_bad_probe_is_refused_with_a_message(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["aistack-boot-facts", "--output", str(tmp_path), "--probe", "nonsense"])

    assert unit.main() == 2
    assert "not a probe" in capsys.readouterr().err


def test_the_script_uses_the_standard_library_only() -> None:
    tree = ast.parse(Path(unit.__file__).read_text(encoding="utf-8"))
    imported = {
        (node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0]
        for node in ast.walk(tree)
        for alias in (node.names if isinstance(node, (ast.Import, ast.ImportFrom)) else [])
    }

    assert imported <= set(sys.stdlib_module_names)


# -- reading ------------------------------------------------------------------------------


def _written(tmp_path: Path, monkeypatch, at: datetime = NOW) -> Path:
    _answers(monkeypatch)
    report = unit.collect(at, {}, "apc@localhost", proc=_proc(tmp_path))
    (tmp_path / FACTS).write_text(json.dumps(report), encoding="utf-8")

    return tmp_path


def test_what_the_unit_wrote_is_read_back(tmp_path: Path, monkeypatch) -> None:
    facts, note = read_facts_file(_written(tmp_path, monkeypatch), NOW + timedelta(minutes=3))

    assert note == "" and facts is not None
    assert facts.booted_at == datetime(2026, 11, 26, 9, 20, tzinfo=timezone.utc) and facts.uptime_seconds == 600
    assert facts.failed_units == () and facts.mounts == ("/", "/mnt/My Share", "/srv")
    assert Container("immich", "running", "unhealthy") in (facts.containers or ())
    assert (facts.docker_user_rules, facts.kvm_modules, facts.previous_boot_clean, facts.ups) == (1, True, True, "OL")


def test_a_source_that_failed_is_none_and_not_an_empty_list(tmp_path: Path, monkeypatch) -> None:
    _answers(monkeypatch, containers="denied", failed_units="denied")
    report = unit.collect(NOW, {}, "", proc=_proc(tmp_path))
    (tmp_path / FACTS).write_text(json.dumps(report), encoding="utf-8")

    facts, _ = read_facts_file(tmp_path, NOW)

    assert facts is not None and facts.containers is None and facts.failed_units is None
    assert facts.sources["containers"] == "error: denied"


def test_a_missing_old_or_damaged_file_says_why_and_is_never_a_healthy_host(tmp_path: Path, monkeypatch) -> None:
    facts, note = read_facts_file(tmp_path / "nowhere", NOW)
    assert facts is None and "install the host unit" in note

    directory = _written(tmp_path, monkeypatch)
    facts, note = read_facts_file(directory, NOW + timedelta(minutes=45))
    assert facts is None and "is old" in note

    (directory / FACTS).write_text("not json", encoding="utf-8")
    assert read_facts_file(directory, NOW) == (None, f"{FACTS} is not readable")
    assert parse_facts('{"collected_at": "yesterday"}') is None
    assert parse_facts("[1]") is None


def test_the_flags_of_a_raspberry_and_its_clock_are_read_and_a_host_without_the_command_is_absent(tmp_path: Path, monkeypatch) -> None:
    assert unit.throttled_flags("throttled=0x50005\n") == 0x50005
    assert unit.throttled_flags("throttled=0x0") == 0
    assert unit.clock_synchronized("yes\n") is True and unit.clock_synchronized("no") is False

    for bad in ("", "temp=1", "throttled=zz"):
        with pytest.raises(OSError):
            unit.throttled_flags(bad)

    with pytest.raises(OSError):
        unit.clock_synchronized("maybe")

    _answers(monkeypatch)
    monkeypatch.setattr(unit.shutil, "which", lambda name: f"/usr/bin/{name}")
    report = unit.collect(NOW, {}, "", proc=_proc(tmp_path))

    assert report["throttled"] == 0x50005 and report["clock_synced"] is True
    assert report["sources"]["throttled"] == "ok"


def test_the_reader_keeps_the_flags_and_the_clock_and_none_when_they_were_not_read() -> None:
    from aistack.boot_checks.facts import parse_facts

    read = parse_facts('{"collected_at": "2026-11-26T10:00:00+00:00", "throttled": 327685, "clock_synced": false}')
    absent = parse_facts('{"collected_at": "2026-11-26T10:00:00+00:00"}')

    assert read is not None and read.throttled == 0x50005 and read.clock_synced is False
    assert absent is not None and absent.throttled is None and absent.clock_synced is None
