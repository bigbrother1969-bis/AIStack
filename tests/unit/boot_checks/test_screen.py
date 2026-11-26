"""The indicator of the strip: how long, how many, and never a green that is old (ADR-0032, B3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aistack.boot_checks.controls import Result
from aistack.boot_checks.screen import Indicator, elapsed, indicator, sentence
from aistack.boot_checks.state import Verdict
from aistack.i18n import translator_for

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=timezone.utc)


def verdict(overall: str = "ok", anomalies: int = 0, checked: datetime = NOW, booted: str | None = "2026-11-26T06:05:27+00:00") -> Verdict:
    return Verdict(overall, anomalies, checked.isoformat(), "boot", booted, (Result("mounts", "ok", "fine", ()),))


def test_a_green_says_how_long_since_the_start_at_the_time_of_the_reading() -> None:
    shown = indicator(verdict(), NOW)

    assert (shown.status, shown.level, shown.elapsed_seconds) == ("ok", "clean", 5 * 3600 + 54 * 60 + 33)
    assert indicator(verdict(), NOW + timedelta(minutes=10)).elapsed_seconds == shown.elapsed_seconds + 600


def test_a_green_with_controls_nobody_declared_says_so() -> None:
    partial = Verdict("ok", 0, NOW.isoformat(), "boot", "2026-11-26T06:05:27+00:00", (Result("mounts", "skipped", "none", ()), Result("ups", "ok", "fine", ())))
    shown = indicator(partial, NOW)

    assert shown.skipped == 1 and shown.level == "clean"
    assert sentence(translator_for("en"), shown)[0] == "Start: all well for 5 h 54 (1 not declared)"


def test_anomalies_are_counted_and_colour_the_badge() -> None:
    assert indicator(verdict("warning", 2), NOW).level == "watch"
    assert indicator(verdict("critical", 1), NOW).level == "alert"
    assert indicator(verdict("pending"), NOW).level == "watch"


def test_no_verdict_an_old_verdict_or_unknown_facts_is_never_green() -> None:
    old = verdict(checked=NOW - timedelta(hours=3))

    assert indicator(None, NOW).status == "unknown"
    assert indicator(old, NOW) == Indicator("unknown", 0, None, "the last check is old (2026-11-26T09:00)")
    assert indicator(verdict("unknown", booted=None), NOW).level == "not-instrumented"
    assert indicator(verdict(booted=None), NOW).status == "unknown"


def test_the_time_is_said_in_days_hours_or_minutes() -> None:
    t = translator_for("en")

    assert elapsed(t, 7 * 60) == "7 min"
    assert elapsed(t, 5 * 3600 + 12 * 60) == "5 h 12"
    assert elapsed(t, 2 * 86400 + 3 * 3600) == "2 d 3 h"


def test_the_sentence_and_its_tooltip_follow_the_status() -> None:
    t = translator_for("en")

    assert sentence(t, Indicator("ok", 0, 3600))[0] == "Start: all well for 1 h 00"
    assert sentence(t, Indicator("critical", 2, 120))[0] == "Start: 2 to fix (since 2 min)"
    assert sentence(t, Indicator("unknown", 0, None, "no facts")) == ("Start: not judged", "The checks could not judge the start: no facts")
