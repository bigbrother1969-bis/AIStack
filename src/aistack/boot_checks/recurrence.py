"""
What comes back (ADR-0032, slice O3): an anomaly that returns at several starts is a finding of its own.

The history (`history.py`) says *since when* a control fails. This reads the same journal for another
question: **which controls start to fail again and again**, at distinct starts of the machine. One failure
is an incident; the same one at three starts in two months is a cause nobody has found, and correcting the
symptom each time will not stop it.

Only what the journal already keeps is read (a control, a status, a date, the start it happened in). An
episode begins when a control goes from not failing (ok, pending, unknown, information, skipped) to
*to watch* or *to fix*; going from *to watch* to *to fix* is the same episode. Failures that stay failing
across a restart without ever being quiet are one episode, not a recurrence: `history.open_since` already
says since when. No statistics, no guess: a count of starts, a window in days, and the owner's two numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from aistack.boot_checks.definition import CRITICAL, WARNING
from aistack.boot_checks.history import Event, _when

FAILING = (WARNING, CRITICAL)
# The control that says what comes back is not itself something that comes back.
OWN = "recurrence"


@dataclass(frozen=True)
class Recurrence:
    """One control that failed again at `starts` distinct starts within the window; `last` is the date (YYYY-MM-DD) of the latest."""

    control: str
    starts: int
    last: str
    open: bool = False


@dataclass(frozen=True)
class RecurrenceReading:
    """
    What the journal says of recurrence: what came back, how far back it looks (`since`, the date of its oldest line
    kept, empty when it holds none), and the owner's threshold, so the control can say what it did *not* find.
    """

    found: tuple[Recurrence, ...] = ()
    since: str = ""
    starts: int = 3
    days: int = 60


def _day(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d")


def read_recurrence(journal: tuple[Event, ...], now: datetime, days: int, starts: int) -> RecurrenceReading:
    """The controls that began to fail at `starts` distinct starts or more in the last `days` days, the most often first."""

    limit = now - timedelta(days=days)
    dated = sorted(((moment, event) for event in journal if (moment := _when(event.at)) is not None), key=lambda pair: pair[0])
    since = _day(dated[0][0]) if dated else ""
    episodes: dict[str, dict[str, datetime]] = {}
    failing: dict[str, bool] = {}

    for moment, event in dated:
        if event.control == OWN:
            continue

        was = failing.get(event.control, False)
        failing[event.control] = event.status in FAILING

        if event.status in FAILING and not was and moment >= limit:
            # Two lines in one start are one start; a line with no start named stands for its own day.
            episodes.setdefault(event.control, {})[event.boot_id or _day(moment)] = moment

    found = [
        Recurrence(control, len(starts_of), _day(max(starts_of.values())), failing.get(control, False))
        for control, starts_of in episodes.items()
        if len(starts_of) >= starts
    ]
    found.sort(key=lambda item: (-item.starts, item.control))

    return RecurrenceReading(tuple(found), since, starts, days)
