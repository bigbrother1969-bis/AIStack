from pathlib import Path

import pytest

from aistack.cli.resource_priority_monitor import (
    USAGE,
    ApplyReport,
    log_cycle,
    parse,
)


def test_parse_defaults_to_the_real_definition_looping_forever():
    definition_path, once, dry_run = parse([])

    assert definition_path.name == "resource_priority.yml"
    assert once is False
    assert dry_run is False


def test_parse_accepts_a_definition_override():
    definition_path, _, _ = parse(["--definition", "/tmp/custom.yml"])

    assert definition_path == Path("/tmp/custom.yml")


def test_parse_accepts_once_and_dry_run_together():
    _, once, dry_run = parse(["--once", "--dry-run"])

    assert once is True
    assert dry_run is True


def test_parse_prints_usage_and_exits_on_help():
    with pytest.raises(SystemExit) as excinfo:
        parse(["--help"])

    assert excinfo.value.code == 0


def test_parse_rejects_an_unknown_argument():
    with pytest.raises(SystemExit) as excinfo:
        parse(["--nonsense"])

    assert excinfo.value.code == 2


def test_usage_names_every_flag_parse_accepts():
    for flag in ("--definition", "--once", "--dry-run"):
        assert flag in USAGE


def test_log_cycle_is_silent_when_nothing_changed(capsys):
    log_cycle(boosted={"jellyfin": False}, report=ApplyReport())

    assert capsys.readouterr().out == ""


def test_log_cycle_prints_when_something_was_applied(capsys):
    log_cycle(
        boosted={"jellyfin": True}, report=ApplyReport(applied=("jellyfin",))
    )

    out = capsys.readouterr().out

    assert "jellyfin=boosted" in out
    assert "applied=['jellyfin']" in out


def test_log_cycle_names_every_priority_app_by_its_own_state(capsys):
    """
    Generalised 2026-09-03: with more than one priority app
    possible, `state=` has to name which app is which rather than
    carry one implied boolean.
    """

    log_cycle(
        boosted={"jellyfin": True, "some-app": False},
        report=ApplyReport(applied=("jellyfin",)),
    )

    out = capsys.readouterr().out

    assert "jellyfin=boosted" in out
    assert "some-app=normal" in out


def test_log_cycle_always_prints_a_labelled_line(capsys):
    """
    The shutdown release is worth a line even when nothing needed
    to change — it is the record that the monitor exited cleanly
    rather than the reason a container quietly stayed throttled.
    """

    log_cycle(boosted={}, report=ApplyReport(), label="releasing on exit")

    assert "releasing on exit" in capsys.readouterr().out


def test_log_cycle_prints_when_a_container_is_not_found(capsys):
    """
    Regression for the 2026-09-03 refactor onto `ApplyReport
    .changed`: `not_found` alone must still print, the same as
    before the print condition became one shared property instead
    of being spelled out here.
    """

    log_cycle(boosted={"jellyfin": False}, report=ApplyReport(not_found=("radarr",)))

    assert "not_found=['radarr']" in capsys.readouterr().out


def test_log_cycle_prints_a_timestamp(capsys):
    """
    Found needed 2026-09-03: a transition observed as "faster than
    the 60-second grace period" had no timestamp on either log line
    to check the claim against. An ISO date at the start of the
    line is enough to compare two prints against a wall clock.
    """

    log_cycle(
        boosted={"jellyfin": True}, report=ApplyReport(applied=("jellyfin",))
    )

    out = capsys.readouterr().out

    assert out[:4].isdigit()  # a year, not "state=..." straight away
    assert "T" in out.split(" ", 1)[0]  # ISO 8601 date/time separator
