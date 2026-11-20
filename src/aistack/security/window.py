"""
The maintenance window (ADR-0028 slice T4a).

The owner says "I am working on the hosts for two hours": during that time
the drift of files and units is counted and not told, since it is his own
doing. Nothing else changes: an open port, a secret, failed logins, the
proxy keep being told. The window is bounded (`window_max_hours`, 4 by
default) and ends by itself; opening and closing are kept in a journal so
that "who silenced the alerts, and when" always has an answer.

Two small files in the data directory: `security-window.json` (the window
that is open, if any) and `security-window.jsonl` (the journal).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

STATE = "security-window.json"
JOURNAL = "security-window.jsonl"

_DURATION = re.compile(r"^\s*(\d+(?:[.,]\d+)?)\s*(h|m|min)?\s*$", re.IGNORECASE)


@dataclass(frozen=True)
class Window:
    opened_at: datetime
    until: datetime

    def remaining(self, now: datetime) -> timedelta:
        return max(self.until - now, timedelta(0))


def zone(name: str) -> timezone | ZoneInfo:
    """The owner's time zone; UTC when the system does not know the name (never an error)."""

    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return timezone.utc


def parse_duration(text: str) -> timedelta:
    """`2h`, `90m`, `1.5h`, or a bare number of hours; anything else is refused."""

    found = _DURATION.match(text)
    if not found:
        raise ValueError(f"not a duration: {text!r} (write 2h or 90m)")

    value = float(found.group(1).replace(",", "."))
    unit = (found.group(2) or "h").lower()
    return timedelta(minutes=value) if unit in ("m", "min") else timedelta(hours=value)


def _instant(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read(generated_dir: Path) -> Window | None:
    """The window on file, expired or not; None when there is none or it cannot be read."""

    try:
        data = json.loads((generated_dir / STATE).read_text(encoding="utf-8"))
        opened, until = _instant(data["opened_at"]), _instant(data["until"])
    except (OSError, ValueError, KeyError, TypeError):
        return None

    return Window(opened, until) if opened and until else None


def current(generated_dir: Path, now: datetime) -> Window | None:
    """The window that is open now."""

    window = read(generated_dir)
    return window if window is not None and now < window.until else None


def _journal(generated_dir: Path, now: datetime, event: str, window: Window | None) -> None:
    line = {"at": now.isoformat(timespec="seconds"), "event": event}
    if window is not None:
        line["opened_at"] = window.opened_at.isoformat(timespec="seconds")
        line["until"] = window.until.isoformat(timespec="seconds")

    generated_dir.mkdir(parents=True, exist_ok=True)
    with (generated_dir / JOURNAL).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(line, ensure_ascii=False) + "\n")


def _write(generated_dir: Path, window: Window | None) -> None:
    path = generated_dir / STATE
    generated_dir.mkdir(parents=True, exist_ok=True)

    if window is None:
        path.unlink(missing_ok=True)
        return

    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {
                "opened_at": window.opened_at.isoformat(timespec="seconds"),
                "until": window.until.isoformat(timespec="seconds"),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def open_window(generated_dir: Path, now: datetime, duration: timedelta, maximum_hours: int) -> Window:
    """Open (or replace) the window for `duration`; refused beyond the declared maximum."""

    if duration <= timedelta(0):
        raise ValueError("the duration must be more than zero")

    if duration > timedelta(hours=maximum_hours):
        raise ValueError(f"a window lasts at most {maximum_hours} h (window_max_hours in security.yml)")

    window = Window(now, now + duration)
    _write(generated_dir, window)
    _journal(generated_dir, now, "opened", window)
    return window


def end(generated_dir: Path, now: datetime) -> bool:
    """Close the window by hand; False when none is open."""

    window = current(generated_dir, now)
    if window is None:
        return False

    _write(generated_dir, None)
    _journal(generated_dir, now, "ended", window)
    return True


def close_if_expired(generated_dir: Path, now: datetime) -> Window | None:
    """Close a window whose time has passed, and say which one; None when there is nothing to close."""

    window = read(generated_dir)
    if window is None or now < window.until:
        return None

    _write(generated_dir, None)
    _journal(generated_dir, now, "expired", window)
    return window
