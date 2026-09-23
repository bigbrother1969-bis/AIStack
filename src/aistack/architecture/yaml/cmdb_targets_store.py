from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.architecture.cmdb_definition import CmdbProbeTargetDefinition

_REQUIRED_TARGET_FIELDS = ("name", "url")


def load_cmdb_probe_targets_yaml(path: Path) -> tuple[CmdbProbeTargetDefinition, ...]:
    """
    Load the governed CMDB probe target list from YAML.

    **Written by hand, read-only** — same reasoning as
    `load_infrastructure_topology_yaml`/`load_service_categorization_yaml`:
    this file is typed by the owner, so a missing key here is a typo,
    and the error names which one and where. Nothing in this
    repository writes it back.

    A single top-level `targets:` key, unlike
    `infrastructure_topology.yml`'s several independently-optional
    blocks — there is only one kind of thing this file declares, so
    a missing or empty `targets:` simply means "nothing to probe yet"
    rather than an error, the same "not filled in yet, not malformed"
    stance `infrastructure_topology.yml`'s own optional keys take.
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
