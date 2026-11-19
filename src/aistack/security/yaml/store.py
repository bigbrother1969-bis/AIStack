from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.security.definition import SecurityDefinition


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

    return SecurityDefinition(
        declared_ports=_ports(data, "declared_ports", path),
        sensitive_ports=_ports(data, "sensitive_ports", path),
        critical_ports=_ports(data, "critical_ports", path),
        max_listed=max_listed,
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
