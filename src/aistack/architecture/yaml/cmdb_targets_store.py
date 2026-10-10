from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.architecture.cmdb_definition import CmdbProbeTargetDefinition

_REQUIRED_TARGET_FIELDS = ("name", "url")


def load_cmdb_probe_targets_yaml(path: Path) -> tuple[CmdbProbeTargetDefinition, ...]:
    """
    Load the CMDB probe target list from YAML.

    The file is written by hand; a missing key raises a `ValueError` naming
    it. A missing or empty `targets:` means nothing to probe.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}

    if not isinstance(data, dict):
        raise ValueError(f"CMDB probe targets must contain a mapping: {path}")

    targets_data = data.get("targets") or []

    if not isinstance(targets_data, list):
        raise ValueError(f"CMDB probe targets {path}: targets must be a list")

    return tuple(
        _load_target(item, path, index) for index, item in enumerate(targets_data)
    )


def _load_target(data: Any, path: Path, index: int) -> CmdbProbeTargetDefinition:
    label = f"CMDB probe targets {path}: targets[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_TARGET_FIELDS, label)

    return CmdbProbeTargetDefinition(name=data["name"], url=data["url"])


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
