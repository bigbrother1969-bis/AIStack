"""
What the vigil tells Gotify about the start-up checks (ADR-0032, slice B6).

One message a day, at `summary.at` in the owner's time zone, and nothing
in between: a finding of the checks never rings by itself. It is read from
the verdicts the checks have just written, never from the hosts, and says
for each machine how long all has been well, or what is to watch, and what
failed since the start and has been resolved. It is told once a day: a
message that Gotify does not take is tried again at the next pass.
Without a verdict of this machine there is nothing to say, and the first pass
of a fresh install only notes the day.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from aistack.boot_checks.controls import ANOMALIES
from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.screen import read_indicators, sentence
from aistack.boot_checks.state import Verdict, read_verdict
from aistack.security.window import zone
from aistack.vigil.notify import Event, State

SHOWN = 3
CRITICAL = "critical"


def _at(value: str) -> tuple[int, int]:
    hour, minute = value.split(":")

    return int(hour), int(minute)


def _label(t: Callable[..., str], control: str) -> str:
    key = f"boot_check.control.{control}"
    said = t(key)

    return control if said == key else said


def _details(t: Callable[..., str], verdict: Verdict | None) -> list[str]:
    """The controls to watch, then what failed since the start and is resolved, a few of each."""

    if verdict is None:
        return []

    lines = [
        t("notify.event.boot_anomaly", control=_label(t, result.control), summary=result.summary)
        for result in verdict.results
        if result.status in ANOMALIES
    ][:SHOWN]
    resolved = [item for item in verdict.incidents if item.resolved_at is not None]
    lines.extend(
        t("notify.event.boot_resolved", control=_label(t, item.control), summary=item.summary)
        for item in resolved[-SHOWN:]
    )

    return lines


def events(
    t: Callable[..., str],
    previous: State,
    generated: Path,
    definition: BootChecksDefinition,
    now: datetime,
    timezone_name: str,
) -> tuple[list[Event], str]:
    """The day's summary, when it is due, and the day to keep."""

    local = now.astimezone(zone(timezone_name))
    today = local.date().isoformat()
    day = previous.boot_summary_day

    if not definition.summary_enabled or day == today or (local.hour, local.minute) < _at(definition.summary_at):
        return [], day

    if read_verdict(generated) is None:
        return [], day

    if not previous.known:
        return [], today

    indicators = read_indicators(generated, now)
    found = [Event("boot", t("notify.event.boot_summary"))]
    urgent = False

    for host, shown in indicators:
        text, _ = sentence(t, shown, host)
        found.append(Event("boot", "· " + text))
        found.extend(Event("boot", "  " + line) for line in _details(t, read_verdict(generated, host)))
        urgent = urgent or shown.status == CRITICAL

    if urgent:
        found = [Event(item.kind, item.line, True) for item in found]

    return found, today
