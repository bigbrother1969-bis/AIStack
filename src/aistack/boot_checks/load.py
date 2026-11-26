from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from aistack.boot_checks.definition import (
    DEFAULT_SEVERITY,
    FINDINGS,
    SEVERITIES,
    BootChecksDefinition,
)

_CLOCK = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def load_boot_checks_yaml(path: Path) -> BootChecksDefinition:
    """Load the start-up checks declaration; a wrong shape raises a `ValueError` naming the file and the key."""

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(f"Boot checks definition must contain a mapping: {path}")

    label = f"Boot checks definition {path}"
    defaults = BootChecksDefinition()
    ai = _section(data, "ai", label)
    summary = _section(data, "summary", label)

    return BootChecksDefinition(
        settle_minutes=_positive_int(
            data, "settle_minutes", defaults.settle_minutes, label
        ),
        expected_containers=_names(
            data.get("expected_containers"), f"{label}: expected_containers"
        ),
        expected_stopped=_names(
            data.get("expected_stopped"), f"{label}: expected_stopped"
        ),
        mounts=_paths(data.get("mounts"), f"{label}: mounts"),
        docker_user_rules=_optional_count(data, "docker_user_rules", label),
        severity=_severity(data.get("severity"), label),
        companions=_flag(data, "companions", defaults.companions, label),
        indicator_weighted=_flag(
            data, "indicator_weighted", defaults.indicator_weighted, label
        ),
        ai_enabled=_flag(ai, "enabled", defaults.ai_enabled, f"{label}: ai"),
        ai_max_extra_controls=_positive_int(
            ai, "max_extra_controls", defaults.ai_max_extra_controls, f"{label}: ai"
        ),
        summary_enabled=_flag(
            summary, "enabled", defaults.summary_enabled, f"{label}: summary"
        ),
        summary_at=_clock(summary, "at", defaults.summary_at, f"{label}: summary"),
    )


def _section(data: dict[str, Any], key: str, label: str) -> dict[str, Any]:
    value = data.get(key)

    if value is None:
        return {}

    if not isinstance(value, dict):
        raise ValueError(f"{label}: {key} must be a mapping")

    return value


def _positive_int(data: dict[str, Any], key: str, default: int, label: str) -> int:
    value = data.get(key, default)

    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label}: {key} must be a positive whole number")

    return value


def _optional_count(data: dict[str, Any], key: str, label: str) -> int | None:
    value = data.get(key)

    if value is None:
        return None

    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(
            f"{label}: {key} must be a whole number, or absent to skip the control"
        )

    return value


def _flag(data: dict[str, Any], key: str, default: bool, label: str) -> bool:
    value = data.get(key, default)

    if not isinstance(value, bool):
        raise ValueError(f"{label}: {key} must be true or false")

    return value


def _clock(data: dict[str, Any], key: str, default: str, label: str) -> str:
    value = data.get(key, default)

    if not isinstance(value, str) or not _CLOCK.match(value):
        raise ValueError(f'{label}: {key} must be a time such as "08:00"')

    return value


def _names(value: Any, label: str) -> tuple[str, ...]:
    if value is None:
        return ()

    if not isinstance(value, list) or not all(
        isinstance(item, str) and item for item in value
    ):
        raise ValueError(f"{label} must be a list of names")

    return tuple(value)


def _paths(value: Any, label: str) -> tuple[str, ...]:
    paths = _names(value, label)

    if not all(item.startswith("/") for item in paths):
        raise ValueError(f"{label} must be absolute paths")

    return paths


def _severity(value: Any, label: str) -> dict[str, str]:
    severity = dict(DEFAULT_SEVERITY)

    if value is None:
        return severity

    if not isinstance(value, dict):
        raise ValueError(
            f"{label}: severity must map a finding to ignore, warning or critical"
        )

    for finding, level in value.items():
        if finding not in FINDINGS:
            raise ValueError(
                f"{label}: severity.{finding} is not a known finding ({', '.join(FINDINGS)})"
            )

        if level not in SEVERITIES:
            raise ValueError(
                f"{label}: severity.{finding} must be one of {', '.join(SEVERITIES)}"
            )

        severity[finding] = level

    return severity
