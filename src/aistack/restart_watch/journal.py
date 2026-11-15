from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

JOURNAL_FILE = "restart-watch.jsonl"
STATE_FILE = "restart-watch-state.json"
# The journal is trimmed to its newest KEPT lines once it passes TRIM_AT.
KEPT = 500
TRIM_AT = 600

# What a line says happened.
RESTARTED = "restarted"
FAILED = "failed"
PLANNED = "planned"  # dry run: what would have been done
SKIPPED_LIMIT = "skipped_limit"
OUTSIDE_WINDOW = "outside_window"
CYCLE = "cycle"  # the declared order loops


@dataclass(frozen=True)
class Entry:
    at: str
    event: str
    container: str
    reasons: tuple[str, ...] = ()
    detail: str = ""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def append(directory: Path, entry: Entry) -> None:
    """One decision, one line; never raises on a full or read-only disk (the watch must go on)."""

    try:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / JOURNAL_FILE
        line = json.dumps(
            {
                "at": entry.at,
                "event": entry.event,
                "container": entry.container,
                "reasons": list(entry.reasons),
                "detail": entry.detail,
            },
            ensure_ascii=False,
        )

        with path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")

        lines = path.read_text(encoding="utf-8").splitlines()

        if len(lines) > TRIM_AT:
            path.write_text("\n".join(lines[-KEPT:]) + "\n", encoding="utf-8")
    except OSError:
        pass


def read(directory: Path, limit: int = 100) -> tuple[Entry, ...]:
    """The newest `limit` decisions, newest first; unreadable lines are skipped."""

    try:
        lines = (directory / JOURNAL_FILE).read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()

    found: list[Entry] = []

    for line in reversed(lines):
        try:
            data = json.loads(line)
            found.append(
                Entry(
                    at=str(data["at"]),
                    event=str(data["event"]),
                    container=str(data["container"]),
                    reasons=tuple(str(r) for r in data.get("reasons") or ()),
                    detail=str(data.get("detail") or ""),
                )
            )
        except (ValueError, KeyError, TypeError):
            continue

        if len(found) >= limit:
            break

    return tuple(found)


def write_state(directory: Path, state: dict[str, Any]) -> None:
    """What the screen shows as "now": the window and who is stuck."""

    try:
        directory.mkdir(parents=True, exist_ok=True)
        temporary = directory / (STATE_FILE + ".tmp")
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        temporary.replace(directory / STATE_FILE)
    except OSError:
        pass


def read_state(directory: Path) -> dict[str, Any]:
    try:
        data = json.loads((directory / STATE_FILE).read_text(encoding="utf-8"))

        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def describe(entries: Sequence[Entry]) -> list[str]:
    """One plain line per entry, for a terminal."""

    return [f"{e.at} {e.event} {e.container} {','.join(e.reasons)} {e.detail}".rstrip() for e in entries]
