from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.restart_watch.definition import Probe, RestartWatchDefinition


def load_restart_watch_yaml(path: Path) -> RestartWatchDefinition:
    """Load the watch's declaration; a wrong shape raises a `ValueError` naming the file and the key."""

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(f"Restart watch definition must contain a mapping: {path}")

    label = f"Restart watch definition {path}"
    defaults = RestartWatchDefinition()

    return RestartWatchDefinition(
        window_minutes=_positive_int(data, "window_minutes", defaults.window_minutes, label),
        poll_seconds=_positive_number(data, "poll_seconds", defaults.poll_seconds, label),
        confirm_cycles=_positive_int(data, "confirm_cycles", defaults.confirm_cycles, label),
        max_attempts_per_hour=_positive_int(
            data, "max_attempts_per_hour", defaults.max_attempts_per_hour, label
        ),
        wait_seconds=_positive_number(data, "wait_seconds", defaults.wait_seconds, label),
        after=_after(data.get("after"), label),
        never=_names(data.get("never"), f"{label}: never"),
        probes=_probes(data.get("probes"), label),
    )


def _positive_number(data: dict[str, Any], key: str, default: float, label: str) -> float:
    value = data.get(key, default)

    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"{label}: {key} must be a positive number")

    return float(value)


def _positive_int(data: dict[str, Any], key: str, default: int, label: str) -> int:
    return int(_positive_number(data, key, default, label))


def _names(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()

    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{label} must be a list of container names")

    return tuple(value)


def _after(value: Any, label: str) -> dict[str, tuple[str, ...]]:
    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(f"{label}: after must map a container to the ones restarted before it")

    return {str(name): _names(first, f"{label}: after.{name}") for name, first in value.items()}


def _probes(value: Any, label: str) -> dict[str, Probe]:
    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(f"{label}: probes must map a container to its probe")

    probes: dict[str, Probe] = {}

    for name, item in value.items():
        if not isinstance(item, dict) or not isinstance(item.get("url"), str) or not item["url"]:
            raise ValueError(f"{label}: probes.{name} needs a url")

        timeout = item.get("timeout_seconds", 5)

        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError(f"{label}: probes.{name}.timeout_seconds must be a positive number")

        probes[str(name)] = Probe(url=item["url"], timeout_seconds=float(timeout))

    return probes
