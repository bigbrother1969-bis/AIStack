from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.arrivals.definition import ArrivalsDefinition


def load_arrivals_yaml(path: Path) -> ArrivalsDefinition:
    """Load the declaration; a wrong shape raises a `ValueError` naming the file and the key."""

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(f"Arrivals definition must contain a mapping: {path}")

    label = f"Arrivals definition {path}"
    defaults = ArrivalsDefinition()

    passes = data.get("confirm_passes", defaults.confirm_passes)

    if isinstance(passes, bool) or not isinstance(passes, int) or passes < 1:
        raise ValueError(f"{label}: confirm_passes must be a whole number of at least 1")

    hours = data.get("machine_scan_hours", defaults.machine_scan_hours)

    if isinstance(hours, bool) or not isinstance(hours, (int, float)) or hours < 0:
        raise ValueError(f"{label}: machine_scan_hours must be 0 (never) or a number of hours")

    return ArrivalsDefinition(
        confirm_passes=passes,
        machine_scan_hours=float(hours),
        ignore=_names(data.get("ignore"), f"{label}: ignore", "container names"),
        known_hosts=_names(data.get("known_hosts"), f"{label}: known_hosts", "addresses"),
    )


def _names(value: Any, label: str, what: str) -> tuple[str, ...]:
    if value is None:
        return ()

    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label} must be a list of {what}")

    return tuple(value)
