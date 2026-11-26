"""The extra controls of a start and the circumstances that justify them (ADR-0032, B5a)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack.boot_checks.catalogue import choose, circumstances, evaluate_extra, settled_since
from aistack.boot_checks.controls import INFORMATION, OK, PENDING, SKIPPED, UNKNOWN, Reading
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.load import load_boot_checks_yaml
from aistack.boot_checks.state import judge, read_verdict, write_verdict
from tests.unit.boot_checks.test_controls import BOOT, LATER, facts

# 07:04 in Paris in November (06:04 UTC): outside the 02:00 to 05:00 window.
DEFINITION = BootChecksDefinition(database_containers=("app_db", "other_db"))


def test_a_clean_ordinary_morning_asks_for_no_extra_control() -> None:
    found = circumstances(facts(previous_boot_clean=True, uptime_seconds=40 * 3600), DEFINITION)

    assert found == () and choose(found, DEFINITION) == ()


def test_a_stop_that_was_not_clean_calls_for_the_databases_and_the_kernel() -> None:
    found = circumstances(facts(previous_boot_clean=False, uptime_seconds=40 * 3600), DEFINITION)

    assert found == ("unclean_previous_stop",)
    assert choose(found, DEFINITION) == ("database_recovery", "kernel_disk_errors")


def test_a_recent_start_tells_its_cause_and_a_ups_stop_is_a_circumstance() -> None:
    found = circumstances(facts(previous_boot_clean=True, stop_reason="ups"), DEFINITION)

    assert found == ("ups_event", "recent_restart")
    assert choose(found, DEFINITION) == ("restart_cause",)


def test_a_ups_that_is_not_on_line_is_an_event_too() -> None:
    assert "ups_event" in circumstances(facts(previous_boot_clean=True, ups="OB DISCHRG", uptime_seconds=40 * 3600), DEFINITION)


def test_a_start_inside_the_backup_window_is_seen_in_the_owner_s_time_zone() -> None:
    inside = datetime(2026, 11, 26, 1, 23, tzinfo=timezone.utc)  # 02:23 in Paris
    found = circumstances(facts(previous_boot_clean=True, booted_at=inside, uptime_seconds=40 * 3600), DEFINITION)

    assert found == ("restart_in_backup_window",) and choose(found, DEFINITION) == ("backup_after_restart",)
    assert circumstances(facts(previous_boot_clean=True, booted_at=inside, uptime_seconds=40 * 3600), BootChecksDefinition(timezone="UTC")) == ()


def test_a_backup_window_may_cross_midnight() -> None:
    crossing = BootChecksDefinition(timezone="UTC", backup_window=("23:00", "01:00"))

    for hour, expected in ((23, True), (0, True), (1, False), (12, False)):
        start = datetime(2026, 11, 26, hour, 30, tzinfo=timezone.utc)

        assert ("restart_in_backup_window" in circumstances(facts(previous_boot_clean=True, booted_at=start, uptime_seconds=40 * 3600), crossing)) is expected


def test_memory_under_pressure_is_a_circumstance_by_the_declared_thresholds() -> None:
    quiet = facts(previous_boot_clean=True, uptime_seconds=40 * 3600, memory_pressure=3.0, swap_used_percent=10)

    assert circumstances(quiet, DEFINITION) == ()
    assert circumstances(facts(previous_boot_clean=True, uptime_seconds=40 * 3600, memory_pressure=12.0), DEFINITION) == ("memory_pressure",)
    assert circumstances(facts(previous_boot_clean=True, uptime_seconds=40 * 3600, swap_used_percent=60), DEFINITION) == ("memory_pressure",)
    assert circumstances(quiet, BootChecksDefinition(memory_pressure_percent=2)) == ("memory_pressure",)


def test_the_extra_controls_are_capped_and_kept_in_catalogue_order() -> None:
    every = ("unclean_previous_stop", "ups_event", "recent_restart", "restart_in_backup_window", "memory_pressure")

    assert choose(every, DEFINITION) == ("database_recovery", "kernel_disk_errors", "restart_cause")
    assert choose(every, BootChecksDefinition(ai_max_extra_controls=5)) == ("database_recovery", "kernel_disk_errors", "restart_cause", "backup_after_restart", "memory")
    assert choose(every, BootChecksDefinition(catalogue={"memory": ("memory_pressure",), "database_recovery": (), "kernel_disk_errors": (), "restart_cause": (), "backup_after_restart": ()})) == ("memory",)


def _results(chosen: tuple[str, ...], settled: bool = True, backup: Reading | None = None, definition: BootChecksDefinition = DEFINITION, **changes: object):
    return {result.control: result for result in evaluate_extra(chosen, facts(**changes), definition, backup, settled)}


def test_database_recovery_names_the_databases_that_recovered_and_never_a_log_line() -> None:
    recovered = _results(("database_recovery",), database_recovery={"app_db": 2, "other_db": 0})["database_recovery"]

    assert recovered.status == "warning" and recovered.finding == "database_recovery"
    assert recovered.details == ("app_db",) and recovered.summary == "1 database(s) recovered after the start"

    quiet = _results(("database_recovery",), database_recovery={"app_db": 0, "other_db": 0})["database_recovery"]

    assert quiet.status == OK


def test_a_database_log_that_was_not_read_is_unknown_never_a_pass() -> None:
    partial = _results(("database_recovery",), database_recovery={"app_db": 0})["database_recovery"]

    assert partial.status == UNKNOWN and partial.details == ("other_db",)
    assert _results(("database_recovery",), database_recovery=None, sources={"database_recovery": "error: nope"})["database_recovery"].status == UNKNOWN


def test_without_a_declared_database_the_control_is_skipped_and_says_so() -> None:
    result = _results(("database_recovery",), definition=BootChecksDefinition(), database_recovery={"x": 1})["database_recovery"]

    assert result.status == SKIPPED and "no database container declared" in result.summary


def test_kernel_disk_errors_are_to_fix_and_counted_not_quoted() -> None:
    failing = _results(("kernel_disk_errors",), kernel_disk_errors=3)["kernel_disk_errors"]

    assert failing.status == "critical" and "3 disk or file-system error line(s)" in failing.summary
    assert _results(("kernel_disk_errors",), kernel_disk_errors=0)["kernel_disk_errors"].status == OK
    assert _results(("kernel_disk_errors",), kernel_disk_errors=None)["kernel_disk_errors"].status == UNKNOWN


def test_the_cause_of_the_stop_is_told_as_information_never_an_anomaly() -> None:
    for reason, said in (("ups", "stopped by the UPS"), ("requested", "asked for"), ("unknown", "not in the journal"), (None, "not known")):
        result = _results(("restart_cause",), stop_reason=reason)["restart_cause"]

        assert result.status == INFORMATION and said in result.summary


def test_the_backup_after_a_restart_in_its_window_reuses_the_backup_domain() -> None:
    assert _results(("backup_after_restart",), backup=Reading(True, 0))["backup_after_restart"].status == OK

    late = _results(("backup_after_restart",), backup=Reading(True, 1))["backup_after_restart"]

    assert late.status == "warning" and late.finding == "backup_late"
    assert _results(("backup_after_restart",), backup=None)["backup_after_restart"].status == SKIPPED
    assert _results(("backup_after_restart",), backup=Reading(False, 0, "no backup instrumented"))["backup_after_restart"].status == SKIPPED


def test_memory_says_its_numbers_and_is_to_watch_when_pressed() -> None:
    calm = _results(("memory",), memory_pressure=1.0, swap_used_percent=5)["memory"]

    assert calm.status == OK and calm.summary == "memory pressure 1.0 %, swap 5 % in use"

    pressed = _results(("memory",), memory_pressure=20.0, swap_used_percent=5)["memory"]

    assert pressed.status == "warning" and pressed.finding == "memory_pressure"
    assert _results(("memory",), memory_pressure=None, swap_used_percent=None)["memory"].status == UNKNOWN


def test_before_the_settle_time_an_extra_finding_is_pending_and_the_owner_may_ignore_it() -> None:
    assert _results(("kernel_disk_errors",), settled=False, kernel_disk_errors=2)["kernel_disk_errors"].status == PENDING

    ignoring = BootChecksDefinition(severity={"kernel_disk_errors": "ignore"})

    assert _results(("kernel_disk_errors",), definition=ignoring, kernel_disk_errors=2)["kernel_disk_errors"].status == SKIPPED


def test_only_the_chosen_controls_answer() -> None:
    assert list(_results(("memory", "restart_cause"), memory_pressure=1.0, swap_used_percent=1)) == ["restart_cause", "memory"]
    assert _results(()) == {}


def test_the_settle_time_is_the_same_rule_as_the_base_controls() -> None:
    assert settled_since(facts(), DEFINITION, LATER) is True
    assert settled_since(facts(), DEFINITION, BOOT + timedelta(minutes=2)) is False


def test_the_verdict_keeps_the_circumstances_and_the_extra_controls_it_chose(tmp_path: Path) -> None:
    found = ("unclean_previous_stop",)
    chosen = choose(found, DEFINITION)
    results = evaluate_extra(chosen, facts(kernel_disk_errors=0, database_recovery={"app_db": 0, "other_db": 0}), DEFINITION, None, True)
    verdict = judge(results, facts(), LATER, None, found, chosen)
    write_verdict(tmp_path, verdict)
    read = read_verdict(tmp_path)

    assert read is not None and read.circumstances == found and read.extra == chosen
    assert [result.control for result in read.results] == ["database_recovery", "kernel_disk_errors"]


def test_an_old_verdict_without_the_new_fields_still_reads(tmp_path: Path) -> None:
    (tmp_path / "boot-check.json").write_text('{"checked_at": "2026-11-26T09:00:00+00:00", "overall": "ok", "anomalies": 0, "results": []}', encoding="utf-8")
    read = read_verdict(tmp_path)

    assert read is not None and read.circumstances == () and read.extra == ()


def test_the_declaration_is_read_and_a_control_or_circumstance_outside_the_closed_lists_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "b.yml"
    path.write_text(
        "database_containers: [a_db]\ntimezone: UTC\nbackup_window: {from: '01:00', until: '04:30'}\nrecent_restart_hours: 6\n"
        "memory_pressure_percent: 25\nswap_used_percent: 80\ncatalogue:\n  memory: [recent_restart]\n",
        encoding="utf-8",
    )
    definition = load_boot_checks_yaml(path)

    assert definition.database_containers == ("a_db",) and definition.timezone == "UTC"
    assert definition.backup_window == ("01:00", "04:30") and definition.recent_restart_hours == 6
    assert (definition.memory_pressure_percent, definition.swap_used_percent) == (25, 80)
    assert definition.catalogue["memory"] == ("recent_restart",) and definition.catalogue["restart_cause"] == ("recent_restart", "ups_event")

    for text in ("catalogue:\n  rm_rf: [recent_restart]\n", "catalogue:\n  memory: [full_moon]\n", "catalogue: 3\n", "timezone: Mars/Base\n", "backup_window: {from: '25:00'}\n"):
        path.write_text(text, encoding="utf-8")

        with pytest.raises(ValueError):
            load_boot_checks_yaml(path)


def test_the_command_adds_the_extra_controls_the_circumstances_call_for_and_says_so(tmp_path: Path, capsys) -> None:
    from aistack.cli import boot_check
    from tests.unit.boot_checks.test_controls import _facts_file

    now = datetime.now(timezone.utc)
    declaration = tmp_path / "b.yml"
    declaration.write_text("database_containers: [app_db]\n", encoding="utf-8")
    _facts_file(
        tmp_path / "facts",
        now,
        previous_boot_clean=False,
        kernel_disk_errors=0,
        database_recovery={"app_db": 1},
        stop_reason="unknown",
    )
    code = boot_check.main(["--once", "--facts", str(tmp_path / "facts"), "--output", str(tmp_path / "out"), "--definition", str(declaration), "--no-cockpit"])
    printed = capsys.readouterr().out
    saved = read_verdict(tmp_path / "out")

    assert code == 1 and "circumstances: unclean_previous_stop" in printed and "database_recovery" in printed
    assert saved is not None and saved.extra == ("database_recovery", "kernel_disk_errors", "restart_cause")


def test_a_clean_ordinary_pass_adds_nothing(tmp_path: Path, capsys) -> None:
    from aistack.cli import boot_check
    from tests.unit.boot_checks.test_controls import _facts_file

    old_start = {"booted_at": "2026-11-23T12:00:00+00:00", "uptime_seconds": 259200, "boot_id": "boot-1"}
    _facts_file(tmp_path / "facts", datetime.now(timezone.utc), previous_boot_clean=True, boot=old_start)
    boot_check.main(["--once", "--facts", str(tmp_path / "facts"), "--output", str(tmp_path / "out"), "--no-cockpit"])
    saved = read_verdict(tmp_path / "out")

    assert saved is not None and saved.extra == () and "circumstances:" not in capsys.readouterr().out
