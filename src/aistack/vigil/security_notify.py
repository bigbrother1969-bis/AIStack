"""
What the vigil tells Gotify about security (ADR-0028 slice T4a).

Read from the report the assessment just wrote, never from the hosts:

- a finding **to fix** or an **urgent** one is told at once, once, and not
  again while it stands; one that goes and comes back is told again. Urgent
  rings (Gotify priority 8), to fix shows;
- the findings **to watch** are told in one message a day, at `digest_hour`
  o'clock in `digest_timezone`, with how long each has stood, and only when
  there are some. One that appears after that hour waits for the next day;
- while a **maintenance window** is open (`aistack.security.window`), the
  drift of files and units is counted, not told, whatever its severity but
  urgent; the day's message says that a window is open and how much it
  holds. A finding held that way is told when the window ends if it still
  stands. A window that runs out by itself is told once;
- the first pass after the slice is installed only notes what is there;
- a report that has not been rewritten for three hours is said in the day's
  message: the vigil that watches would itself have stopped watching.

Nothing here acts on any host: a false alert costs a message, never an
outage (the lesson of 2026-11-19).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from aistack.i18n import Translator
from aistack.security.definition import SecurityDefinition
from aistack.security.findings import FIX, URGENT, WATCH
from aistack.security.window import Window, zone
from aistack.vigil.notify import Event, State

# What a window holds back: the drift of files and units (`drift.<host>.…`).
HELD_PREFIX = "drift."
STALE_AFTER = timedelta(hours=3)
EVIDENCE_LINES = 3


@dataclass(frozen=True)
class Outcome:
    events: list[Event]
    told: tuple[str, ...]
    watch_since: dict[str, str]
    digest_day: str
    known: bool


def _instant(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    raw = report.get("findings")
    found = [item for item in raw if isinstance(item, dict) and isinstance(item.get("key"), str)] if isinstance(raw, list) else []
    return found


def _held(finding: dict[str, Any], in_window: bool) -> bool:
    return in_window and str(finding["key"]).startswith(HELD_PREFIX) and finding.get("severity") != URGENT


def _age(t: Translator, since: datetime | None, now: datetime) -> str:
    if since is None or now - since < timedelta(hours=1):
        return t("notify.age.recent")

    hours = int((now - since).total_seconds() // 3600)
    return t("notify.age.hours", n=hours) if hours < 48 else t("notify.age.days", n=hours // 24)


def events(
    t: Translator,
    previous: State,
    report: dict[str, Any] | None,
    opened: Window | None,
    expired: Window | None,
    now: datetime,
    definition: SecurityDefinition,
) -> Outcome:
    found: list[Event] = []

    if expired is not None and previous.known:
        found.append(Event("security", t("notify.event.security_window_expired")))

    if report is None:
        return Outcome(found, previous.security_told, previous.watch_since, previous.digest_day, previous.security_known)

    findings = _findings(report)
    in_window = opened is not None
    local = now.astimezone(zone(definition.digest_timezone))
    today = local.date().isoformat()
    first = not previous.security_known

    # To fix and urgent: told once while they stand.
    serious = {item["key"]: item for item in findings if item.get("severity") in (FIX, URGENT)}
    told = {key for key in previous.security_told if key in serious}

    for key, item in serious.items():
        if key in told or _held(item, in_window):
            continue
        told.add(key)
        if first or not previous.known:
            continue
        urgent = item.get("severity") == URGENT
        found.append(Event("security", t("notify.event.security_urgent" if urgent else "notify.event.security_fix", title=item.get("title", key)), urgent=urgent))
        for line in [str(value) for value in item.get("evidence") or []][:EVIDENCE_LINES]:
            found.append(Event("security", "· " + line, urgent=urgent))

    # To watch: how long each has stood, and one message a day.
    watching = {item["key"]: item for item in findings if item.get("severity") == WATCH}
    since = {key: value for key, value in previous.watch_since.items() if key in watching}
    for key in watching:
        since.setdefault(key, now.isoformat(timespec="seconds"))

    digest_day = previous.digest_day

    if local.hour >= definition.digest_hour and previous.digest_day != today:
        digest_day = today
        shown = [item for item in watching.values() if not _held(item, in_window)]
        held = len(watching) - len(shown)
        collected = _instant(report.get("collected_at"))
        stale = collected is None or now - collected > STALE_AFTER
        lines: list[str] = []

        if shown:
            lines.append(t("notify.event.security_digest", count=len(shown)))
            for item in shown:
                lines.append("· " + t("notify.event.security_digest_item", title=item.get("title", item["key"]), age=_age(t, _instant(since.get(item["key"])), now)))

        if opened is not None and held:
            until = opened.until.astimezone(zone(definition.digest_timezone)).strftime("%H:%M")
            lines.append(("· " if lines else "") + t("notify.event.security_digest_window", until=until, held=held))

        if stale:
            lines.append(("· " if lines else "") + t("notify.event.security_stale", hours=int((now - collected) // timedelta(hours=1)) if collected else 0))

        if lines and not first and previous.known:
            found.append(Event("security", lines[0]))
            found.extend(Event("security", line if line.startswith("· ") else "· " + line) for line in lines[1:])

    return Outcome(found, tuple(sorted(told)), since, digest_day, True)
