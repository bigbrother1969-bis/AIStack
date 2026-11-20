from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.security.definition import DRIFT_NOISE, DRIFT_SENSITIVE, SecurityDefinition
from aistack.security.hygiene import ACCEPTABLE


def load_security_yaml(path: Path) -> SecurityDefinition:
    """
    Load the security declaration from YAML. Every key is optional: an
    absent map is empty, so a declaration that says nothing declares
    nothing. A port must be an integer from 1 to 65535.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if data is None:
        data = {}

    if not isinstance(data, dict):
        raise ValueError(f"Security declaration must contain a mapping: {path}")

    max_listed = data.get("max_listed", 20)

    if isinstance(max_listed, bool) or not isinstance(max_listed, int) or max_listed < 1:
        raise ValueError(f"Security declaration {path}: max_listed must be a positive integer")

    max_age = data.get("max_image_age_days", 365)

    if isinstance(max_age, bool) or not isinstance(max_age, int) or max_age < 1:
        raise ValueError(f"Security declaration {path}: max_image_age_days must be a positive integer")

    reboot_days = _positive(data, "max_reboot_pending_days", 14, path)
    apt_days = _positive(data, "max_apt_age_days", 7, path)

    return SecurityDefinition(
        declared_ports=_ports(data, "declared_ports", path),
        sensitive_ports=_ports(data, "sensitive_ports", path),
        critical_ports=_ports(data, "critical_ports", path),
        accepted=_accepted(data, path),
        max_image_age_days=max_age,
        max_reboot_pending_days=reboot_days,
        max_apt_age_days=apt_days,
        accepted_files=_paths(data, path),
        max_listed=max_listed,
        drift_window_hours=_positive(data, "drift_window_hours", 24, path),
        drift_apt_grace_minutes=_positive(data, "drift_apt_grace_minutes", 60, path),
        drift_sensitive=_patterns(data, "drift_sensitive", DRIFT_SENSITIVE, path),
        drift_noise=_patterns(data, "drift_noise", DRIFT_NOISE, path),
        accepted_drift=_patterns(data, "accepted_drift", (), path),
    )


def _ports(data: dict[str, Any], key: str, path: Path) -> dict[int, str]:
    declared = data.get(key) or {}

    if not isinstance(declared, dict):
        raise ValueError(f"Security declaration {path}: {key} must be a mapping of port to purpose")

    ports: dict[int, str] = {}

    for port, purpose in declared.items():
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError(f"Security declaration {path}: {key}: {port!r} is not a port (1 to 65535)")
        ports[port] = str(purpose or "")

    return ports


def _accepted(data: dict[str, Any], path: Path) -> dict[str, tuple[str, ...]]:
    declared = data.get("accepted") or {}

    if not isinstance(declared, dict):
        raise ValueError(f"Security declaration {path}: accepted must be a mapping of a kind of risk to container names")

    accepted: dict[str, tuple[str, ...]] = {}

    for kind, names in declared.items():
        if kind not in ACCEPTABLE:
            raise ValueError(f"Security declaration {path}: accepted: {kind!r} is not one of {', '.join(ACCEPTABLE)}")
        if not isinstance(names, list) or not all(isinstance(name, str) and name for name in names):
            raise ValueError(f"Security declaration {path}: accepted: {kind} must be a list of container names")
        accepted[kind] = tuple(names)

    return accepted


def _positive(data: dict[str, Any], key: str, default: int, path: Path) -> int:
    value = data.get(key, default)

    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"Security declaration {path}: {key} must be a positive integer")

    return value


def _paths(data: dict[str, Any], path: Path) -> tuple[str, ...]:
    declared = data.get("accepted_files") or []

    if not isinstance(declared, list) or not all(isinstance(item, str) and item.startswith("/") for item in declared):
        raise ValueError(f"Security declaration {path}: accepted_files must be a list of absolute paths")

    return tuple(declared)


def _patterns(data: dict[str, Any], key: str, default: tuple[str, ...], path: Path) -> tuple[str, ...]:
    if key not in data or data[key] is None:
        return default

    declared = data[key]

    if not isinstance(declared, list) or not all(isinstance(item, str) and item for item in declared):
        raise ValueError(f"Security declaration {path}: {key} must be a list of path patterns")

    return tuple(declared)
