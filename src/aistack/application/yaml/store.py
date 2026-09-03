from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.kernel.application import ApplicationDefinition, SyncthingDefinition

_REQUIRED_FIELDS = (
    "app_id",
    "title",
    "view_id",
    "source_root",
    "target_root",
    "selection_file",
)

_REQUIRED_SYNCTHING_FIELDS = (
    "url",
    "folder_id",
)


def load_application_definition_yaml(path: Path) -> ApplicationDefinition:
    """
    Load a governed application definition from YAML.

    **Written by hand, not generated.** `load_catalog_yaml` and
    `load_selection_yaml` read artefacts a program wrote, so a
    missing key there is corruption and a bare `KeyError` says
    enough. This file is typed by the owner, so a missing key here
    is a typo, and the error names which one rather than pointing
    at a line inside this module.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(
            f"Application definition must contain a mapping: {path}"
        )

    _require(data, _REQUIRED_FIELDS, f"Application definition {path}")

    syncthing_data = data.get("syncthing")

    return ApplicationDefinition(
        app_id=data["app_id"],
        title=data["title"],
        view_id=data["view_id"],
        source_root=data["source_root"],
        target_root=data["target_root"],
        selection_file=data["selection_file"],
        capacity_declared_bytes=int(data.get("capacity_declared_bytes") or 0),
        syncthing=_load_syncthing(syncthing_data, path) if syncthing_data else None,
    )


def _load_syncthing(data: Any, path: Path) -> SyncthingDefinition:
    if not isinstance(data, dict):
        raise ValueError(
            f"Application definition {path}: syncthing must be a mapping"
        )

    _require(
        data,
        _REQUIRED_SYNCTHING_FIELDS,
        f"Application definition {path}: syncthing",
    )

    return SyncthingDefinition(
        url=data["url"],
        folder_id=data["folder_id"],
        device_id=data.get("device_id", ""),
        api_key_env=data.get("api_key_env", ""),
        timeout_seconds=float(data.get("timeout_seconds") or 5.0),
    )


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
