"""The numbers behind a report, and their series (ADR-0028 T4a)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.hosts.records import HostRecords, HostsDeclaration
from aistack.security import series
from aistack.security.definition import SecurityDefinition
from aistack.security.findings import FIX, INFORMATION, WATCH, Finding
from aistack.security.host import Packages, Upgrade
from aistack.security.logs import HostLogs
from aistack.security.measures import measures
from aistack.security.refusals import Sample

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
DEFINITION = SecurityDefinition()


def _logs() -> HostLogs:
    data = {
        "ssh": {"failed": {"lan": 1, "vpn": 0, "outside": 5, "unknown": 0}, "invalid_user": {"outside": 2}},
        "kernel": {"docker_user_refuse": {"outside": 7}},
        "npm": {
            "requests": 100,
            "probes_by_origin": {"outside": 4},
            "app_paths_by_origin": {"outside": 30, "lan": 1},
            "vhosts": {"a": {"probes_ok": 0, "app_paths_ok": 20}, "b": {"probes_ok": 1, "app_paths_ok": 2}},
        },
    }
    return HostLogs(NOW, 24, {"ssh": "ok", "kernel": "ok", "npm": "ok"}, data)


def _all() -> dict[str, int]:
    findings = [
        Finding("exposure.port.22", WATCH, "t"),
        Finding("drift.pi.sensitive", WATCH, "t"),
        Finding("hygiene.docker", FIX, "t"),
        Finding("logs.ssh", INFORMATION, "t"),
    ]
    refusals = [
        Sample(NOW - timedelta(hours=2), "b", {"docker_user": 10, "input_policy": 0, "ufw": 0, "other": 0}),
        Sample(NOW - timedelta(hours=1), "b", {"docker_user": 40, "input_policy": 5, "ufw": 0, "other": 0}),
    ]
    packages = Packages(NOW, (Upgrade("a", "1", "2", True), Upgrade("b", "1", "2", False)), NOW - timedelta(days=3, hours=2), NOW)
    return measures(
        findings=findings,
        listening=12,
        published=30,
        refusals=refusals,
        logs=[("local", _logs(), ""), ("pi", None, "not read")],
        drift=([], None),
        packages=[("local", packages), ("pi", None)],
        old_images=2,
        now=NOW,
        definition=DEFINITION,
    )


def test_the_measures_are_counts_by_class_and_by_host() -> None:
    found = _all()

    assert found["findings.watch"] == 2 and found["findings.fix"] == 1 and found["findings.urgent"] == 0
    assert found["area.drift.watch"] == 1 and found["area.hygiene.fix"] == 1
    assert found["ports.listening"] == 12 and found["ports.published"] == 30
    assert found["refusals.docker_user"] == 30 and found["refusals.input_policy"] == 5
    assert found["refusals.covered_minutes"] == 60
    assert found["ssh.local.failed.outside"] == 5 and found["ssh.local.invalid_user.outside"] == 2
    assert found["kernel.local.docker_user_refuse.outside"] == 7
    assert found["npm.local.requests"] == 100 and found["npm.local.app_paths.outside"] == 30
    assert found["npm.local.probes_answered"] == 1 and found["npm.local.app_paths_answered"] == 22
    assert found["packages.local.updates"] == 2 and found["packages.local.security"] == 1
    assert found["packages.local.reboot_days"] == 3
    assert found["images.old"] == 2


def test_a_source_that_was_not_read_adds_no_key() -> None:
    found = _all()

    assert not [key for key in found if ".pi." in key]
    assert measures(
        findings=[], listening=0, published=None, refusals=None, logs=[], drift=([], None), packages=[], old_images=None,
        now=NOW, definition=DEFINITION,
    ).keys() == {"findings.information", "findings.watch", "findings.fix", "findings.urgent", "ports.listening"}


def test_a_measure_names_no_address_path_or_content() -> None:
    for key, value in _all().items():
        assert isinstance(value, int)
        assert all(character.isalnum() or character in "._-" for character in key)


def test_a_host_with_records_is_counted_by_class() -> None:
    from aistack.security.drift import host_counts

    event = {"at": (NOW - timedelta(minutes=30)).isoformat(), "kind": "file", "action": "modified", "path": "/etc/passwd"}
    ordinary = {"at": (NOW - timedelta(minutes=20)).isoformat(), "kind": "file", "action": "modified", "path": "/etc/motd"}
    records = HostRecords("pi", Path("/x"), {"last_run": NOW.isoformat()}, [(1, event), (2, ordinary)])
    declaration = HostsDeclaration((), timedelta(minutes=1500))

    counted = host_counts(records, declaration.silent_after, NOW, DEFINITION)
    assert counted is not None and counted["sensitive"] == 1 and counted["other"] == 1


def _report(generated: Path, collected: datetime, measures_: dict[str, int]) -> None:
    (generated / series.REPORT).write_text(
        json.dumps({"security": {"collected_at": collected.isoformat(), "measures": measures_}}), encoding="utf-8"
    )


def test_a_report_is_appended_once(tmp_path: Path) -> None:
    _report(tmp_path, NOW, {"findings.watch": 2})

    assert series.append(tmp_path, NOW, False, 90) is True
    assert series.append(tmp_path, NOW + timedelta(minutes=15), False, 90) is False

    _report(tmp_path, NOW + timedelta(minutes=15), {"findings.watch": 3})
    assert series.append(tmp_path, NOW + timedelta(minutes=16), True, 90) is True

    lines = series.read(tmp_path)
    assert [line["measures"]["findings.watch"] for line in lines] == [2, 3]
    assert [line["window"] for line in lines] == [False, True]


def test_nothing_is_appended_without_a_readable_report(tmp_path: Path) -> None:
    assert series.append(tmp_path, NOW, False, 90) is False
    (tmp_path / series.REPORT).write_text("{broken", encoding="utf-8")
    assert series.append(tmp_path, NOW, False, 90) is False
    _report(tmp_path, NOW, {})
    (tmp_path / series.REPORT).write_text(json.dumps({"security": {"collected_at": NOW.isoformat()}}), encoding="utf-8")
    assert series.append(tmp_path, NOW, False, 90) is False
    assert not (tmp_path / series.SERIES).exists()


def test_old_lines_are_dropped_and_a_bad_line_is_skipped(tmp_path: Path) -> None:
    _report(tmp_path, NOW - timedelta(days=100), {"findings.watch": 1})
    series.append(tmp_path, NOW - timedelta(days=100), False, 365)
    with (tmp_path / series.SERIES).open("a", encoding="utf-8") as stream:
        stream.write("not json\n")

    _report(tmp_path, NOW, {"findings.watch": 4})
    assert series.append(tmp_path, NOW, False, 90) is True

    assert [line["measures"]["findings.watch"] for line in series.read(tmp_path)] == [4]
