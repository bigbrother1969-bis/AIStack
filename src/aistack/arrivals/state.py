"""
What the vigil has seen (`arrivals-state.json`, written only by the
vigil) and what the owner decided (`arrivals-decisions.json`, written
only by the screen). Two files, so a decision clicked during a pass is
never overwritten by it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATE_FILE = "arrivals-state.json"
DECISIONS_FILE = "arrivals-decisions.json"
OBSERVATION_FILE = "network-docker-observation.json"


def _read(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}

    return data if isinstance(data, dict) else {}


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_state(directory: Path) -> dict[str, Any]:
    """The last pass: `containers`, `hosts`, `known_hosts`, `baseline`, `last_scan`, `updated_at`; `{}` before the first."""

    return _read(directory / STATE_FILE)


def write_state(directory: Path, state: dict[str, Any]) -> None:
    _write(directory / STATE_FILE, state)


def read_decisions(directory: Path) -> dict[str, list[str]]:
    data = _read(directory / DECISIONS_FILE)

    return {
        key: sorted({str(item) for item in data.get(key) or [] if item})
        for key in ("ignored_containers", "known_hosts")
    }


def write_decisions(directory: Path, decisions: dict[str, list[str]]) -> None:
    _write(directory / DECISIONS_FILE, decisions)


def read_observation(directory: Path) -> dict[str, Any]:
    """The last network discovery (`network_docker_discover`), `{}` when there is none or it is unreadable."""

    return _read(directory / OBSERVATION_FILE)
