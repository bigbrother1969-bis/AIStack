from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    JellyfinPriorityDefinition,
    ResourcePriorityDefinition,
)

_REQUIRED_FIELDS = ("jellyfin", "background", "unlimited_cpus")
_REQUIRED_JELLYFIN_FIELDS = ("container", "normal_cpus", "boosted_cpus", "url")
_REQUIRED_BACKGROUND_FIELDS = ("default_throttled_cpus", "containers")
_REQUIRED_CONTAINER_FIELDS = ("name",)


def load_resource_priority_yaml(path: Path) -> ResourcePriorityDefinition:
    """
    Load the governed resource-priority definition from YAML.

    **Written by hand, not generated** — same reasoning as
    `load_application_definition_yaml`: this file is typed by the
    owner, so a missing key here is a typo, and the error names
    which one and where, rather than pointing at a line inside this
    module.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(
            f"Resource priority definition must contain a mapping: {path}"
        )

    _require(data, _REQUIRED_FIELDS, f"Resource priority definition {path}")

    return ResourcePriorityDefinition(
        jellyfin=_load_jellyfin(data["jellyfin"], path),
        background=_load_background(data["background"], path),
        unlimited_cpus=float(data["unlimited_cpus"]),
    )


def _load_jellyfin(data: Any, path: Path) -> JellyfinPriorityDefinition:
    label = f"Resource priority definition {path}: jellyfin"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_JELLYFIN_FIELDS, label)

    return JellyfinPriorityDefinition(
        container=data["container"],
        normal_cpus=float(data["normal_cpus"]),
        boosted_cpus=float(data["boosted_cpus"]),
        url=data["url"],
        api_key_env=data.get("api_key_env", ""),
        timeout_seconds=float(data.get("timeout_seconds") or 5.0),
    )


def _load_background(data: Any, path: Path) -> BackgroundPriorityDefinition:
    label = f"Resource priority definition {path}: background"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_BACKGROUND_FIELDS, label)

    containers_data = data["containers"]

    if not isinstance(containers_data, list):
        raise ValueError(f"{label}.containers must be a list")

    return BackgroundPriorityDefinition(
        default_throttled_cpus=float(data["default_throttled_cpus"]),
        containers=tuple(
            _load_container(item, path, index)
            for index, item in enumerate(containers_data)
        ),
    )


def _load_container(
    data: Any, path: Path, index: int
) -> ContainerPriorityDefinition:
    label = f"Resource priority definition {path}: background.containers[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_CONTAINER_FIELDS, label)

    normal_cpus = data.get("normal_cpus")

    return ContainerPriorityDefinition(
        name=data["name"],
        normal_cpus=float(normal_cpus) if normal_cpus is not None else None,
    )


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
