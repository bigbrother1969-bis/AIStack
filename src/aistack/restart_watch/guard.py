from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

HOUR_SECONDS = 3600.0
ATTEMPTS_FILE = "restart-watch-attempts.json"

Attempts = dict[str, list[float]]


def allowed(attempts: Mapping[str, list[float]], name: str, now: float, maximum: int) -> bool:
    """Whether `name` may be restarted again: fewer than `maximum` attempts in the last hour."""

    recent = [moment for moment in attempts.get(name, ()) if now - moment < HOUR_SECONDS]

    return len(recent) < maximum


def record(attempts: Attempts, name: str, now: float) -> None:
    """Note one attempt, dropping what is older than the hour that counts."""

    attempts[name] = [m for m in attempts.get(name, []) if now - m < HOUR_SECONDS] + [now]


def read_attempts(directory: Path) -> Attempts:
    """The attempts kept across a restart of the watch; an unreadable file counts as none."""

    try:
        data = json.loads((directory / ATTEMPTS_FILE).read_text(encoding="utf-8"))

        return {str(k): [float(v) for v in values] for k, values in data.items()}
    except (OSError, ValueError, TypeError, AttributeError):
        return {}


def write_attempts(directory: Path, attempts: Mapping[str, list[float]]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    temporary = directory / (ATTEMPTS_FILE + ".tmp")
    temporary.write_text(json.dumps(attempts, indent=1) + "\n", encoding="utf-8")
    temporary.replace(directory / ATTEMPTS_FILE)
