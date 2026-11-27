"""What comes back: a control that began to fail at several distinct starts (O3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.boot_checks.controls import INFORMATION, OK, SKIPPED, WARNING, Result, evaluate
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.history import Event
from aistack.boot_checks.load import load_boot_checks_yaml
from aistack.boot_checks.phrases import say
from aistack.boot_checks.recurrence import Recurrence, RecurrenceReading, read_recurrence
from aistack.i18n import translator_for
from tests.unit.boot_checks.test_controls import LATER, facts

NOW = datetime(2026, 11, 26, 21, 0, tzinfo=timezone.utc)


def line(days_ago: float, control: str, status: str, boot: str) -> Event:
    return Event((NOW - timedelta(days=days_ago)).isoformat(), control, status, f"{control} {status}", (), boot)


def test_a_control_that_fails_again_at_three_distinct_starts_is_a_recurrence() -> None:
    journal = (
        line(40, "database_recovery", "warning", "b1"),
        line(39.9, "database_recovery", "ok", "b1"),
        line(20, "database_recovery", "warning", "b2"),
        line(19.9, "database_recovery", "ok", "b2"),
        line(2, "database_recovery", "warning", "b3"),
    )
    reading = read_recurrence(journal, NOW, 60, 3)

    assert reading.found == (Recurrence("database_recovery", 3, "2026-11-24", True),)
    assert reading.since == "2026-10-17"


def test_two_starts_are_not_enough_and_one_long_failure_is_not_a_recurrence() -> None:
    twice = (line(30, "mounts", "critical", "b1"), line(29, "mounts", "ok", "b1"), line(5, "mounts", "critical", "b2"))
    long = (line(30, "mounts", "warning", "b1"), line(20, "mounts", "critical", "b2"), line(10, "mounts", "warning", "b3"))

    assert read_recurrence(twice, NOW, 60, 3).found == ()
    assert read_recurrence(long, NOW, 60, 3).found == ()


def test_several_episodes_in_one_start_are_one_start_and_a_line_without_a_start_stands_for_its_day() -> None:
    flapping = (
        line(3, "monitor", "warning", "b1"),
        line(2.9, "monitor", "ok", "b1"),
        line(2.8, "monitor", "warning", "b1"),
        line(2.7, "monitor", "ok", "b1"),
        line(2.6, "monitor", "warning", "b1"),
    )
    bare = (line(9, "monitor", "warning", ""), line(8.9, "monitor", "ok", ""), line(5, "monitor", "warning", ""), line(4.9, "monitor", "ok", ""), line(1, "monitor", "warning", ""))

    assert read_recurrence(flapping, NOW, 60, 3).found == ()
    assert read_recurrence(bare, NOW, 60, 3).found == (Recurrence("monitor", 3, "2026-11-25", True),)


def test_what_is_older_than_the_window_does_not_count_and_a_recovered_one_is_not_open() -> None:
    journal = (
        line(100, "backup", "warning", "b0"),
        line(99, "backup", "ok", "b0"),
        line(30, "backup", "warning", "b1"),
        line(29, "backup", "ok", "b1"),
        line(10, "backup", "warning", "b2"),
        line(9, "backup", "ok", "b2"),
        line(2, "backup", "warning", "b3"),
        line(1, "backup", "ok", "b3"),
    )
    reading = read_recurrence(journal, NOW, 60, 3)

    assert reading.found == (Recurrence("backup", 3, "2026-11-24", False),)
    assert read_recurrence(journal, NOW, 120, 3).found[0].starts == 4


def test_a_control_that_is_not_read_in_between_ends_the_episode_and_the_most_frequent_comes_first() -> None:
    journal = [line(50 - 10 * index, "disks", "warning" if index % 2 == 0 else "unknown", f"b{index}") for index in range(5)]
    journal += [line(45 - 10 * index, "mounts", "critical" if index % 2 == 0 else "ok", f"c{index}") for index in range(4)]
    journal += [line(48 - 5 * index, "domains", "ok" if index % 2 == 0 else "critical", f"d{index}") for index in range(9)]
    reading = read_recurrence(tuple(journal), NOW, 60, 2)

    assert [item.control for item in reading.found] == ["domains", "disks", "mounts"]
    assert read_recurrence((), NOW, 60, 3) == RecurrenceReading((), "", 3, 60)


def test_the_control_that_says_it_is_never_counted_and_an_unreadable_date_is_skipped() -> None:
    own = tuple(line(30 - 10 * index, "recurrence", "warning" if index % 2 == 0 else "ok", f"b{index}") for index in range(5))
    broken = (Event("not a date", "mounts", "warning", "x", (), "b"),)

    assert read_recurrence(own, NOW, 60, 2).found == ()
    assert read_recurrence(broken, NOW, 60, 1) == RecurrenceReading((), "", 1, 60)


def control(reading: RecurrenceReading | None, definition: BootChecksDefinition | None = None) -> Result:
    results = evaluate(facts(), definition or BootChecksDefinition(), LATER, recurrence=reading)

    return next(result for result in results if result.control == "recurrence")


def test_what_has_not_been_read_nor_recorded_is_never_a_green() -> None:
    assert control(None).status == SKIPPED
    assert control(RecurrenceReading()).status == INFORMATION
    assert control(RecurrenceReading()).summary == "no change recorded yet, nothing to compare"


def test_nothing_that_came_back_passes_and_says_since_when_it_looked() -> None:
    result = control(RecurrenceReading((), "2026-11-26", 3, 60))

    assert result.status == OK
    assert result.summary == "no anomaly came back at 3 starts or more since 2026-11-26"


def test_a_recurrence_failing_now_is_to_watch_and_one_all_quiet_is_only_said() -> None:
    now = RecurrenceReading((Recurrence("database_recovery", 3, "2026-11-24", True), Recurrence("backup", 4, "2026-11-20", False)), "2026-10-17", 3, 60)
    past = RecurrenceReading((Recurrence("backup", 4, "2026-11-20", False),), "2026-10-17", 3, 60)
    failing = control(now)
    quiet = control(past)

    assert failing.status == WARNING
    assert failing.finding == "anomaly_recurring"
    assert failing.summary == "2 anomaly(ies) came back at several starts"
    assert failing.details[0] == "database_recovery: back at 3 starts in 60 days, the last on 2026-11-24, failing now"
    assert failing.details[1] == "backup: back at 4 starts in 60 days, the last on 2026-11-20"
    assert failing.details[-1].startswith("to do: find what brings them back")
    assert quiet.status == INFORMATION
    assert quiet.summary == "1 anomaly(ies) came back at several starts, none now"


def test_the_owner_may_ignore_the_finding_or_make_it_heavier() -> None:
    reading = RecurrenceReading((Recurrence("database_recovery", 3, "2026-11-24", True),), "2026-10-17", 3, 60)

    assert control(reading, BootChecksDefinition(severity={"anomaly_recurring": "ignore"})).status == SKIPPED
    assert control(reading, BootChecksDefinition(severity={"anomaly_recurring": "critical"})).status == "critical"


def test_the_declaration_sets_the_window_and_the_number_of_starts(tmp_path: Path) -> None:
    custom = tmp_path / "boot_checks.yml"
    custom.write_text("recurrence_days: 30\nrecurrence_starts: 2\n", encoding="utf-8")

    assert (BootChecksDefinition().recurrence_days, BootChecksDefinition().recurrence_starts) == (60, 3)
    assert (load_boot_checks_yaml(custom).recurrence_days, load_boot_checks_yaml(custom).recurrence_starts) == (30, 2)


def test_the_sentences_are_told_in_both_languages_with_the_control_by_its_title() -> None:
    fr = translator_for("fr")
    en = translator_for("en")
    summary = "1 anomaly(ies) came back at several starts"
    detail = "database_recovery: back at 3 starts in 60 days, the last on 2026-11-24, failing now"
    unknown = "some_extra: back at 3 starts in 60 days, the last on 2026-11-24"

    assert say(fr, summary) == "1 anomalie(s) revenue(s) à plusieurs démarrages"
    assert say(fr, detail) == "Récupération des bases de données : revenue à 3 démarrages en 60 jours, la dernière fois le 2026-11-24, en échec en ce moment"
    assert say(en, detail) == "Database recovery: back at 3 starts in 60 days, the last on 2026-11-24, failing now"
    assert say(en, unknown) == unknown


def test_the_command_reads_the_journal_of_this_machine_and_says_what_came_back(tmp_path: Path, capsys) -> None:
    import json

    from aistack.cli import boot_check
    from tests.unit.boot_checks.test_controls import _facts_file

    now = datetime.now(timezone.utc)
    out = tmp_path / "out"
    out.mkdir()
    rows = []

    for index, days in enumerate((40, 20, 2)):
        for delta, status in ((0, "warning"), (0.1, "ok")):
            at = (now - timedelta(days=days) + timedelta(days=delta)).isoformat()
            rows.append({"at": at, "control": "failed_units", "status": status, "summary": "x", "details": [], "boot_id": f"b{index}"})

    (out / "boot-history.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    _facts_file(tmp_path / "facts", now)

    boot_check.main(["--once", "--facts", str(tmp_path / "facts"), "--output", str(out), "--no-cockpit", "--dry-run"])
    printed = capsys.readouterr().out

    assert "recurrence" in printed and "1 anomaly(ies) came back at several starts, none now" in printed
