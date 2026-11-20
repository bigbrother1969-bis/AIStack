"""What changed on the traced hosts, read from the ADR-0020 records (ADR-0028 T3a)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.hosts.records import HostRecords, HostsDeclaration
from aistack.security.definition import SecurityDefinition
from aistack.security.drift import assess_drift, assess_host_drift
from aistack.security.findings import INFORMATION, WATCH
from aistack.security.yaml import load_security_yaml

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)
SILENT = timedelta(minutes=1500)
DEFINITION = SecurityDefinition()


def _at(minutes_ago: float) -> str:
    return (NOW - timedelta(minutes=minutes_ago)).isoformat()


def _file(path: str, minutes_ago: float = 30, action: str = "modified") -> dict:
    return {"at": _at(minutes_ago), "host": "h", "kind": "file", "action": action, "path": path,
            "before": {"fp": "AAAA"}, "after": {"fp": "BBBB"}}


def _unit(unit: str, before: str | None, after: str | None, minutes_ago: float = 30) -> dict:
    return {"at": _at(minutes_ago), "host": "h", "kind": "unit", "unit": unit, "before": before, "after": after}


def _apt(minutes_ago: float, minutes: float = 5) -> dict:
    return {"at": _at(minutes_ago), "host": "h", "kind": "apt", "ended": _at(minutes_ago - minutes), "counts": {"upgrade": 3}}


def _records(events: list[dict], last_run_minutes_ago: float = 5, problem: str = "") -> HostRecords:
    return HostRecords(
        "h", Path("/x"), {"last_run": _at(last_run_minutes_ago)},
        [(number, event) for number, event in enumerate(events, start=1)], problem,
    )


def _by_key(findings):
    return {finding.key: finding for finding in findings}


def test_a_change_to_a_sensitive_path_is_to_watch_and_names_path_and_action_only() -> None:
    findings = _by_key(assess_host_drift(_records([_file("/etc/sudoers.d/x", action="added")]), SILENT, NOW, DEFINITION))

    finding = findings["drift.h.sensitive"]
    assert finding.severity == WATCH
    assert finding.evidence == ("added /etc/sudoers.d/x",)
    assert "AAAA" not in str(finding.as_dict()) and "BBBB" not in str(finding.as_dict())


def test_an_apt_run_that_just_ended_explains_a_sensitive_change() -> None:
    events = [_apt(40), _file("/etc/passwd", minutes_ago=25)]

    findings = _by_key(assess_host_drift(_records(events), SILENT, NOW, DEFINITION))

    assert "drift.h.sensitive" not in findings
    assert "1 sensitive change(s) explained by an apt run" in findings["drift.h.summary"].evidence


def test_a_sensitive_change_long_after_the_apt_run_is_not_explained() -> None:
    events = [_apt(600), _file("/etc/passwd", minutes_ago=25)]

    assert "drift.h.sensitive" in _by_key(assess_host_drift(_records(events), SILENT, NOW, DEFINITION))


def test_noise_and_accepted_paths_are_counted_never_reported() -> None:
    definition = SecurityDefinition(accepted_drift=("/usr/local/sbin/recours-*",))
    events = [
        _file("/etc/cups/subscriptions.conf"),
        _file("/etc/fake-hwclock.data"),
        _file("/etc/default/docker.dpkg-new", action="added"),
        _file("/usr/local/sbin/recours-collecte"),
    ]

    findings = _by_key(assess_host_drift(_records(events), SILENT, NOW, definition))

    assert "drift.h.sensitive" not in findings
    assert "4 counted as noise or accepted" in findings["drift.h.summary"].evidence


def test_other_files_are_a_count_in_one_information_finding() -> None:
    findings = assess_host_drift(_records([_file("/srv/x/docker-compose.yml"), _file("/etc/motd")]), SILENT, NOW, DEFINITION)

    assert [finding.key for finding in findings] == ["drift.h.summary"]
    assert findings[0].severity == INFORMATION
    assert "2 other file change(s)" in findings[0].evidence


def test_a_unit_newly_enabled_is_to_watch_a_unit_already_enabled_is_not() -> None:
    events = [_unit("evil.service", None, "enabled"), _unit("a.timer", "enabled", "enabled-runtime"), _unit("b.service", "enabled", "disabled")]

    findings = _by_key(assess_host_drift(_records(events), SILENT, NOW, DEFINITION))

    assert findings["drift.h.sensitive"].evidence == ("unit enabled evil.service",)


def test_events_outside_the_window_are_not_read() -> None:
    events = [_file("/etc/passwd", minutes_ago=24 * 60 + 5)]

    assert assess_host_drift(_records(events), SILENT, NOW, DEFINITION) == []


def test_a_silent_host_and_an_unreadable_one_are_findings_about_the_source() -> None:
    silent = assess_host_drift(_records([], last_run_minutes_ago=3000), SILENT, NOW, DEFINITION)
    unread = assess_host_drift(HostRecords("h", Path("/x"), problem="not mounted"), SILENT, NOW, DEFINITION)

    assert [finding.key for finding in silent] == ["drift.h.silent"]
    assert [finding.key for finding in unread] == ["drift.h.unread"] and unread[0].evidence == ("not mounted",)
    assert {finding.severity for finding in silent + unread} == {INFORMATION}


def test_a_quiet_host_has_no_finding_and_no_declaration_means_nothing_to_judge() -> None:
    assert assess_host_drift(_records([]), SILENT, NOW, DEFINITION) == []
    assert assess_drift([_records([_file("/etc/passwd")])], None, NOW, DEFINITION) == []


def test_drift_never_goes_past_watch() -> None:
    events = [_file("/etc/shadow"), _file("/etc/ssh/sshd_config"), _unit("x.service", None, "enabled")]
    declaration = HostsDeclaration((), SILENT)

    findings = assess_drift([_records(events)], declaration, NOW, DEFINITION)

    assert {finding.severity for finding in findings} <= {INFORMATION, WATCH}


def test_long_lists_are_cut_at_max_listed() -> None:
    definition = SecurityDefinition(max_listed=2)
    events = [_file(f"/etc/ssh/k{n}", action="added") for n in range(5)]

    finding = _by_key(assess_host_drift(_records(events), SILENT, NOW, definition))["drift.h.sensitive"]

    assert len(finding.evidence) == 3 and finding.evidence[-1] == "and 3 more"


def test_the_declaration_reads_the_drift_keys_with_defaults_and_rejects_a_bad_list(tmp_path: Path) -> None:
    empty = tmp_path / "a.yml"
    empty.write_text("", encoding="utf-8")
    custom = tmp_path / "b.yml"
    custom.write_text("drift_window_hours: 6\naccepted_drift:\n  - /etc/x/*\n", encoding="utf-8")
    bad = tmp_path / "c.yml"
    bad.write_text("drift_noise: nope\n", encoding="utf-8")

    default = load_security_yaml(empty)
    chosen = load_security_yaml(custom)

    assert default.drift_window_hours == 24 and "/etc/cups/*" in default.drift_noise and "/etc/ssh/*" in default.drift_sensitive
    assert chosen.drift_window_hours == 6 and chosen.accepted_drift == ("/etc/x/*",)
    try:
        load_security_yaml(bad)
    except ValueError as error:
        assert "drift_noise" in str(error)
    else:
        raise AssertionError("a bad list must be refused")


def test_the_task_reads_the_records_of_the_hosts_hosts_yml_traces(tmp_path: Path, monkeypatch) -> None:
    import json

    from aistack.tasks.security_assess import read_drift

    folder = tmp_path / "hosts" / "pi"
    folder.mkdir(parents=True)
    (folder / "host.json").write_text(json.dumps({"last_run": NOW.isoformat()}), encoding="utf-8")
    (folder / "events.jsonl").write_text(json.dumps(_file("/etc/passwd")) + "\n", encoding="utf-8")
    hosts = tmp_path / "hosts.yml"
    hosts.write_text(f"silent_after_minutes: 1500\nhosts:\n  pi:\n    directory: {folder}\n", encoding="utf-8")

    monkeypatch.setenv("AISTACK_CONFIG_DIR", str(tmp_path))
    records, declaration = read_drift(tmp_path)

    assert declaration is not None and [item.host for item in records] == ["pi"]
    assert [finding.key for finding in assess_drift(records, declaration, NOW, DEFINITION)] == ["drift.pi.sensitive", "drift.pi.summary"]
