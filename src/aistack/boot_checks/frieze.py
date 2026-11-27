"""
What happened just before an anomaly (ADR-0032, slice O8): a short frieze of dated facts, never a cause.

When a control starts to fail, the first question is *what changed just before?* The answer is already
recorded: the host started (and how its previous run ended), a container died, was removed or turned
unhealthy, packages changed on a machine, a declaration was written from a screen, another control began to
fail. This gathers those facts from what AIStack already keeps, keeps the ones inside a window before the
anomaly (six hours by default), and says them in one sentence each, oldest first, ending at the anomaly.

It says *before*, never *because*: two things that happened one after the other are not one the cause of the
other, and the code that judges does not guess. Only names and dates are kept, never a line of a log, a label
or an environment variable. The frieze is computed **once**, when the anomaly is first seen (the window before
it is then complete), and stored with the incident, so a long-lived one costs nothing at each pass.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aistack.boot_checks.definition import BootChecksDefinition
from aistack.boot_checks.history import QUIET, Event, _when

OWN = "recurrence"
# Kinds said once per machine with a count, since forty package changes are one fact, not forty.
COUNTED = ("packages", "files")


@dataclass(frozen=True)
class Moment:
    """One recorded fact: when, what kind, about which name (a container, a machine, a file), and how many it stands for."""

    at: datetime
    kind: str
    subject: str = ""
    detail: str = ""
    count: int = 1


def _utc(moment: datetime) -> datetime:
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=timezone.utc)


def sentence(moment: Moment) -> str:
    """The moment as one English sentence (the owner's language is applied by `phrases.say`)."""

    stamp = _utc(moment.at).astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M")
    name = moment.subject
    said = {
        "died": f"{name}: exited with code {moment.detail}",
        "oom": f"{name}: killed for lack of memory",
        "unhealthy": f"{name}: became unhealthy",
        "removed": f"{name}: container removed",
        "restarted": f"{name}: restarted",
        "started": "the host started",
        "started_unclean": "the host started after a stop that was not a shutdown",
        "packages": f"{name}: {moment.count} package change(s)",
        "files": f"{name}: {moment.count} file change(s)",
        "unit": f"{name}: unit {moment.detail} changed",
        "declaration": f"{name}: declaration changed",
        "control": f"{name}: began to fail",
    }

    return f"{stamp} UTC — {said.get(moment.kind, f'{name}: {moment.kind}')}"


def _instant(value: object) -> datetime | None:
    try:
        return _utc(datetime.fromisoformat(str(value)))
    except ValueError:
        return None


def docker_moments(events: Iterable[Mapping[str, Any]]) -> list[Moment]:
    """
    A container that exited with a code other than 0, was killed for memory, turned unhealthy, was removed (an update
    or a retirement) or was restarted. Everything else Docker says (a network connecting, a command run) is left out,
    and the same fact repeated within a minute is said once.
    """

    found: list[Moment] = []
    last: dict[tuple[str, str], datetime] = {}

    for event in events:
        action = str(event.get("action", ""))
        at = _instant(event.get("occurred_at"))
        raw = event.get("raw")
        attributes = raw.get("Actor", {}).get("Attributes", {}) if isinstance(raw, dict) and isinstance(raw.get("Actor"), dict) else {}
        attributes = attributes if isinstance(attributes, dict) else {}
        name = str(event.get("subject") or attributes.get("name") or "")

        if at is None or not name:
            continue

        if action == "die":
            code = str(attributes.get("exitCode", ""))
            moment = Moment(at, "died", name, code) if code.isdigit() and code != "0" else None
        elif action == "oom":
            moment = Moment(at, "oom", name)
        elif action == "health_status: unhealthy":
            moment = Moment(at, "unhealthy", name)
        elif action == "destroy":
            moment = Moment(at, "removed", name)
        elif action == "restart":
            moment = Moment(at, "restarted", name)
        else:
            moment = None

        if moment is None:
            continue

        key = (moment.kind, name)

        if key in last and abs((at - last[key]).total_seconds()) < 60:
            continue

        last[key] = at
        found.append(moment)

    return found


def host_moments(records: Iterable[tuple[str, Iterable[Mapping[str, Any]]]]) -> list[Moment]:
    """What the collector of each traced machine recorded: packages and files changed (counted later), a unit enabled or disabled."""

    found: list[Moment] = []

    for host, events in records:
        for event in events:
            at = _instant(event.get("at"))
            kind = event.get("kind")

            if at is None:
                continue

            if kind == "package":
                found.append(Moment(at, "packages", host))
            elif kind == "file":
                found.append(Moment(at, "files", host))
            elif kind == "unit" and event.get("unit"):
                found.append(Moment(at, "unit", host, str(event["unit"])))

    return found


def declaration_moments(entries: Iterable[Mapping[str, Any]]) -> list[Moment]:
    """A declaration written from a screen (its file name and date, never its content)."""

    found = []

    for entry in entries:
        at = _instant(entry.get("at"))

        if at is not None and entry.get("path"):
            found.append(Moment(at, "declaration", Path(str(entry["path"])).name))

    return found


def journal_moments(journal: Iterable[Event], skip: str | None = None) -> list[Moment]:
    """Another control that began to fail (`skip` is the one the frieze is for, and the control that says what comes back is never one)."""

    found = []

    for event in journal:
        at = _when(event.at)

        if at is not None and event.status not in QUIET and event.control not in (skip, OWN):
            found.append(Moment(at, "control", event.control))

    return found


def start_moment(booted_at: datetime | None, clean: bool | None) -> list[Moment]:
    """The start of the host, said with how the previous run ended when it did not end with a shutdown."""

    if booted_at is None:
        return []

    return [Moment(booted_at, "started" if clean is not False else "started_unclean")]


def _merge(moments: list[Moment]) -> list[Moment]:
    """Several changes of one kind on one machine are one fact with a count, dated by the last."""

    merged: dict[tuple[str, str], Moment] = {}
    rest = []

    for moment in sorted(moments, key=lambda item: item.at):
        if moment.kind in COUNTED:
            key = (moment.kind, moment.subject)
            was = merged.get(key)
            merged[key] = replace(moment, count=(was.count if was else 0) + 1)
        else:
            rest.append(moment)

    return sorted([*rest, *merged.values()], key=lambda item: item.at)


def before(first_seen: datetime, moments: Iterable[Moment], hours: int, limit: int) -> tuple[str, ...]:
    """
    The sentences of what was recorded in the `hours` before `first_seen`, oldest first, the `limit` nearest to the anomaly;
    when there are more, the first line says how many were left out. An empty result means nothing was recorded, which is
    said as such by the page, never as "nothing happened".
    """

    end = _utc(first_seen)
    inside = [moment for moment in moments if end - timedelta(hours=hours) <= _utc(moment.at) <= end]
    ordered = _merge(inside)
    shown = ordered[-limit:]
    left = len(ordered) - len(shown)
    lines = [sentence(moment) for moment in shown]

    return (f"{left} earlier event(s) not shown", *lines) if left else tuple(lines)


def window_start(first_seens: Iterable[str], definition: BootChecksDefinition) -> datetime | None:
    """How far back the records must be read to build the frieze of these incidents; `None` when there is none to build."""

    moments = [moment for moment in (_instant(stamp) for stamp in first_seens) if moment is not None]

    return min(moments) - timedelta(hours=definition.frieze_hours) if moments else None
