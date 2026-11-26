"""The journal of what changed between two verdicts (ADR-0032, slice O2)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aistack.boot_checks.controls import Result
from aistack.boot_checks.history import Event, Retention, history_file, open_since, prune, read_history, transitions
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.load import load_boot_checks_yaml
from aistack.boot_checks.state import Verdict, read_verdict, write_history, write_verdict
from tests.unit.web.test_boot_check_screen import client
from tests.unit.web_signed_in import signed_in

NOW = datetime(2026, 11, 26, 18, 0, tzinfo=timezone.utc)


def verdict(at: datetime, *results: Result, boot: str = "b") -> Verdict:
    return Verdict("ok", 0, at.isoformat(timespec="seconds"), boot, None, results)


def at(minutes: int) -> datetime:
    return NOW + timedelta(minutes=minutes)


def test_a_control_that_starts_to_fail_and_one_that_comes_back_are_two_lines() -> None:
    fine = verdict(at(0), Result("systems", "ok", "4 system(s) read, none down, none under pressure"))
    broken = verdict(at(15), Result("systems", "warning", "4 system(s) read; 2 system(s) down", ("msi", "gigabyte")))
    mended = verdict(at(30), Result("systems", "ok", "4 system(s) read, none down, none under pressure"))

    assert transitions(None, fine) == []
    start = transitions(fine, broken)
    back = transitions(broken, mended)

    assert [(e.control, e.status, e.details) for e in start] == [("systems", "warning", ("msi", "gigabyte"))]
    assert [(e.control, e.status) for e in back] == [("systems", "ok")]
    assert start[0].at == "2026-11-26T18:15:00+00:00"


def test_a_pass_that_changes_nothing_writes_nothing_and_quiet_states_are_not_events() -> None:
    same = Result("disks", "warning", "1 disk failing")

    assert transitions(verdict(at(0), same), verdict(at(15), same)) == []
    assert transitions(verdict(at(0), Result("ups", "skipped", "x")), verdict(at(15), Result("ups", "ok", "y"))) == []
    assert transitions(verdict(at(0), Result("memory", "pending", "x")), verdict(at(15), Result("memory", "information", "y"))) == []
    # a change of weight is a line; a first pass that already fails is one too
    assert len(transitions(verdict(at(0), same), verdict(at(15), Result("disks", "critical", "1 disk failing")))) == 1
    assert len(transitions(None, verdict(at(0), same))) == 1
    assert len(transitions(verdict(at(0), same), verdict(at(15), Result("disks", "unknown", "not read")))) == 1


def test_the_names_kept_with_a_line_are_bounded() -> None:
    names = tuple(f"unit-{n}" for n in range(30))
    found = transitions(None, verdict(at(0), Result("failed_units", "warning", "30 unit(s) failed", names)))

    assert found[0].details == names[:8]


def test_since_when_is_the_first_line_after_the_last_quiet_one() -> None:
    events = (
        Event("2026-11-20T01:00:00", "systems", "warning", "x"),
        Event("2026-11-21T01:00:00", "systems", "ok", "x"),
        Event("2026-11-22T04:51:40", "systems", "warning", "x"),
        Event("2026-11-24T00:00:00", "systems", "critical", "x"),
        Event("2026-11-23T00:00:00", "disks", "warning", "x"),
    )

    assert open_since(events, "systems") == "2026-11-22T04:51:40"
    assert open_since(events, "disks") == "2026-11-23T00:00:00"
    assert open_since(events, "mounts") is None
    assert open_since((*events, Event("2026-11-25T00:00:00", "systems", "ok", "x")), "systems") is None


def test_the_journal_is_bounded_by_age_and_by_number_and_the_oldest_go_first() -> None:
    events = tuple(Event((NOW - timedelta(days=days)).isoformat(timespec="seconds"), "c", "warning", str(days)) for days in (400, 200, 100, 3, 2, 1))

    assert [e.summary for e in prune(events, NOW, Retention(days=180, events=100))] == ["100", "3", "2", "1"]
    assert [e.summary for e in prune(events, NOW, Retention(days=180, events=2))] == ["2", "1"]
    # a date without an offset is read as UTC; one that is not a date is dropped, not a crash
    odd = (Event("2026-11-25T12:00:00", "c", "warning", "naive"), Event("yesterday", "c", "warning", "bad"))

    assert [e.summary for e in prune(odd, NOW, Retention())] == ["naive"]


def test_record_appends_atomically_trims_and_survives_a_damaged_line(tmp_path: Path) -> None:
    write_history(tmp_path, [Event(NOW.isoformat(), "systems", "warning", "2 system(s) down", ("msi",))], NOW)
    path = tmp_path / history_file()
    path.write_text(path.read_text() + "this is not json\n" + json.dumps({"control": "no-date"}) + "\n", encoding="utf-8")
    write_history(tmp_path, [Event(at(15).isoformat(), "systems", "ok", "none down")], at(15))

    found = read_history(tmp_path)

    assert [(e.status, e.details) for e in found] == [("warning", ("msi",)), ("ok", ())]
    assert read_history(tmp_path / "nowhere") == ()
    assert not [p for p in tmp_path.iterdir() if p.suffix not in (".jsonl",)]


def test_a_companion_has_its_own_journal_and_a_bad_name_is_refused(tmp_path: Path) -> None:
    assert history_file(None) == "boot-history.jsonl"
    assert history_file("raspberry") == "boot-history-raspberry.jsonl"

    with pytest.raises(ValueError):
        history_file("../x")


def test_writing_the_verdict_journals_the_change_and_a_journal_that_cannot_be_written_stops_nothing(tmp_path: Path) -> None:
    fine = verdict(at(0), Result("systems", "ok", "fine"))
    broken = verdict(at(15), Result("systems", "warning", "1 system(s) down", ("gigabyte",)))

    write_verdict(tmp_path, fine)
    write_verdict(tmp_path, broken)
    write_verdict(tmp_path, broken)

    assert [(e.control, e.status) for e in read_history(tmp_path)] == [("systems", "warning")]

    (tmp_path / history_file()).unlink()
    (tmp_path / history_file()).mkdir()
    write_verdict(tmp_path, fine)

    found = read_verdict(tmp_path)

    assert found is not None and found.results[0].status == "ok"


def test_the_owner_sets_how_long_and_how_many_and_the_defaults_are_stated(tmp_path: Path) -> None:
    declared = tmp_path / "b.yml"
    declared.write_text("history_days: 30\nhistory_events: 50\n", encoding="utf-8")

    owned = load_boot_checks_yaml(declared)

    assert (owned.history_days, owned.history_events) == (30, 50)
    assert (BootChecksDefinition().history_days, BootChecksDefinition().history_events) == (180, 2000)


def test_the_page_says_since_when_and_lists_the_changes_with_their_names(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    ok = Result("systems", "ok", "4 system(s) read, none down, none under pressure")
    down = Result("systems", "warning", "4 system(s) read; 2 system(s) down", ("msi", "gigabyte"))
    write_verdict(tmp_path, verdict(now - timedelta(days=4), ok))
    write_verdict(tmp_path, verdict(now - timedelta(days=4) + timedelta(minutes=15), down))
    write_verdict(tmp_path, verdict(now, down))

    page = signed_in(client(tmp_path)).get("/boot-check/?lang=en").text

    assert "History" in page and "<code>msi</code>" in page and "<code>gigabyte</code>" in page
    assert f"since {(now - timedelta(days=4) + timedelta(minutes=15)).strftime('%Y-%m-%d %H:%M')}" in page
    assert "No change recorded yet." not in page


def test_the_page_without_any_change_says_so(tmp_path: Path) -> None:
    write_verdict(tmp_path, verdict(datetime.now(timezone.utc), Result("mounts", "ok", "fine")))

    assert "No change recorded yet." in signed_in(client(tmp_path)).get("/boot-check/?lang=en").text
    assert TestClient is not None
