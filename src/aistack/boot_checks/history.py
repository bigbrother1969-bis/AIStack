"""
The history of the verdicts (ADR-0032, slice O2): since when a control has been in the state it is in.

`boot-check.json` is the state of the last pass; it forgets the day before. This journal keeps what
changed: one line when a control **starts to fail**, becomes unknown or changes its weight, and one
when it **comes back**. A pass that changes nothing writes nothing, so the file stays small whatever
the rhythm of the vigil (a pass every 15 minutes is 96 a day, not 96 lines).

What is kept is the names and the sentence of the control as it was then, never a line of a log, so a
past incident still says *which* machine or container, not only how many. The journal is bounded by age
and by number of lines (the owner's, in `boot_checks.yml`); the oldest go first. Best effort: a
journal that cannot be written never stops the verdict from being written (the writing is in `state.py`, with
the other state this service keeps for itself).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aistack.boot_checks.controls import INFORMATION, OK, PENDING, SKIPPED

if TYPE_CHECKING:
    from aistack.boot_checks.state import Verdict

HISTORY = "boot-history.jsonl"
# A control in one of these says nothing happened (pending is the few minutes after a start).
QUIET = (OK, INFORMATION, SKIPPED, PENDING)
# Names kept with a line: enough to say which, not a list.
MAX_NAMES = 8


@dataclass(frozen=True)
class Retention:
    """How long, and how many lines, the journal keeps."""

    days: int = 180
    events: int = 2000


DEFAULT_RETENTION = Retention()


@dataclass(frozen=True)
class Event:
    at: str
    control: str
    status: str
    summary: str
    details: tuple[str, ...] = ()
    boot_id: str = ""


def history_file(host: str | None = None) -> str:
    """`boot-history.jsonl` for this host, `boot-history-<host>.jsonl` for a companion (same plain-name rule as the verdict)."""

    from aistack.boot_checks.state import state_file

    if host is None:
        return HISTORY

    state_file(host)  # refuses a name that is not a plain host name

    return f"boot-history-{host}.jsonl"


def transitions(previous: Verdict | None, verdict: Verdict) -> list[Event]:
    """What changed between two verdicts, as lines: a control that fails, changes its status, or comes back."""

    before = {result.control: result.status for result in previous.results} if previous is not None else {}
    found = []

    for result in verdict.results:
        was = before.get(result.control)

        if was == result.status:
            continue

        if (was is None or was in QUIET) and result.status in QUIET:
            continue

        found.append(Event(verdict.checked_at, result.control, result.status, result.summary, tuple(result.details[:MAX_NAMES]), verdict.boot_id))

    return found


def _event(raw: Any) -> Event | None:
    if not isinstance(raw, dict):
        return None

    try:
        details = raw.get("details", [])

        return Event(
            str(raw["at"]),
            str(raw["control"]),
            str(raw["status"]),
            str(raw.get("summary", "")),
            tuple(str(item) for item in details) if isinstance(details, list) else (),
            str(raw.get("boot_id", "")),
        )
    except KeyError:
        return None


def read_history(directory: Path, host: str | None = None) -> tuple[Event, ...]:
    """The journal, oldest first; a line that cannot be read is skipped, a missing file is an empty history."""

    try:
        lines = (directory / history_file(host)).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()

    found = []

    for line in lines:
        try:
            event = _event(json.loads(line))
        except ValueError:
            continue

        if event is not None:
            found.append(event)

    return tuple(found)


def _when(stamp: str) -> datetime | None:
    """A stamp as a moment, in UTC when it carries no offset; `None` when it is not one."""

    try:
        moment = datetime.fromisoformat(stamp)
    except ValueError:
        return None

    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def prune(events: tuple[Event, ...], now: datetime, keep: Retention) -> tuple[Event, ...]:
    """Drop what is older than the retention (a line whose date cannot be read goes too), then the oldest beyond the number kept."""

    limit = now - timedelta(days=keep.days)
    recent = [event for event in events if (moment := _when(event.at)) is not None and moment >= limit]

    return tuple(recent[-keep.events :])


def open_since(events: tuple[Event, ...], control: str) -> str | None:
    """When the control began to be in a state to watch: the first line after its last quiet one; `None` if it never was."""

    since = None

    for event in events:
        if event.control != control:
            continue

        since = None if event.status in QUIET else (since or event.at)

    return since
