from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.architecture.topology_definition import (
    BeszelConnectionDefinition,
    ExternalNodeDefinition,
    HardwareProfileDefinition,
    InfrastructureTopologyDefinition,
)

_REQUIRED_EXTERNAL_NODE_FIELDS = ("name", "role")
_REQUIRED_HARDWARE_FIELDS = ("name", "model", "role", "cpu", "ram", "storage", "os")
_REQUIRED_BESZEL_FIELDS = ("url", "email_env", "password_env")


def load_infrastructure_topology_yaml(path: Path) -> InfrastructureTopologyDefinition:
    """
    Load the governed infrastructure topology from YAML.

    **Written by hand, read-only** — same reasoning as
    `load_service_categorization_yaml`: nothing in this repository
    observes a registrar, a CDN, or a machine's own BIOS, so there is
    no provider to reconcile this against and no UI that writes it
    back. Both top-level keys are optional and default to an empty
    list — a file declaring only `hardware:`, or only
    `external_nodes:`, is not malformed, it is simply not filled in
    yet.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Infrastructure topology must contain a mapping: {path}")

    external_nodes_data = data.get("external_nodes") or []
    hardware_data = data.get("hardware") or []
    beszel_data = data.get("beszel")

    if not isinstance(external_nodes_data, list):
        raise ValueError(f"Infrastructure topology {path}: external_nodes must be a list")

    if not isinstance(hardware_data, list):
        raise ValueError(f"Infrastructure topology {path}: hardware must be a list")

    return InfrastructureTopologyDefinition(
        external_nodes=tuple(
            _load_external_node(item, path, index)
            for index, item in enumerate(external_nodes_data)
        ),
        hardware=tuple(
            _load_hardware(item, path, index)
            for index, item in enumerate(hardware_data)
        ),
        beszel=_load_beszel(beszel_data, path) if beszel_data is not None else None,
    )


def _load_external_node(
    data: Any, path: Path, index: int
) -> ExternalNodeDefinition:
    label = f"Infrastructure topology {path}: external_nodes[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_EXTERNAL_NODE_FIELDS, label)

    return ExternalNodeDefinition(
        name=data["name"],
        role=data["role"],
        description=data.get("description") or "",
    )


def _load_hardware(data: Any, path: Path, index: int) -> HardwareProfileDefinition:
    label = f"Infrastructure topology {path}: hardware[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_HARDWARE_FIELDS, label)

    return HardwareProfileDefinition(
        name=data["name"],
        model=data["model"],
        role=data["role"],
        cpu=data["cpu"],
        ram=data["ram"],
        storage=data["storage"],
        os_name=data["os"],
        gpu=data.get("gpu") or None,
    )


def _load_beszel(data: Any, path: Path) -> BeszelConnectionDefinition:
    label = f"Infrastructure topology {path}: beszel"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_BESZEL_FIELDS, label)

    return BeszelConnectionDefinition(
        url=data["url"],
        email_env=data["email_env"],
        password_env=data["password_env"],
    )


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
