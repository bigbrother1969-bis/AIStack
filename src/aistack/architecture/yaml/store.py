from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.architecture.definition import (
    ServiceCategorizationDefinition,
    ServiceCategoryDefinition,
    ServiceDefinition,
)

_REQUIRED_CATEGORY_FIELDS = ("name", "services")
_REQUIRED_SERVICE_FIELDS = ("name",)


def load_service_categorization_yaml(path: Path) -> ServiceCategorizationDefinition:
    """
    Load the governed service categorization from YAML.

    **Written by hand, read-only** — same reasoning as
    `load_resource_priority_yaml`: this file is typed by the owner (or
    ported once, as it was 2026-09-10, from `homepage/services.yaml`),
    so a missing key here is a typo, and the error names which one and
    where. Unlike `resource_priority.yml`, nothing in this repository
    writes this file back yet — no `save_service_categorization_yaml`
    exists because no UI edits this categorization the way
    `priority_ui` edits resource priority. Add one only once something
    needs it; until then, editing is by hand, in this file, on disk.
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(f"Service categorization must contain a mapping: {path}")

    if "categories" not in data:
        raise ValueError(f"Service categorization {path} is missing: categories")

    categories_data = data["categories"]

    if not isinstance(categories_data, list):
        raise ValueError(
            f"Service categorization {path}: categories must be a list"
        )

    return ServiceCategorizationDefinition(
        categories=tuple(
            _load_category(item, path, index)
            for index, item in enumerate(categories_data)
        )
    )


def _load_category(
    data: Any, path: Path, index: int
) -> ServiceCategoryDefinition:
    label = f"Service categorization {path}: categories[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_CATEGORY_FIELDS, label)

    services_data = data["services"]

    if not isinstance(services_data, list):
        raise ValueError(f"{label}.services must be a list")

    return ServiceCategoryDefinition(
        name=data["name"],
        services=tuple(
            _load_service(item, path, index, service_index)
            for service_index, item in enumerate(services_data)
        ),
    )


def _load_service(
    data: Any, path: Path, category_index: int, service_index: int
) -> ServiceDefinition:
    label = (
        f"Service categorization {path}: "
        f"categories[{category_index}].services[{service_index}]"
    )

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    _require(data, _REQUIRED_SERVICE_FIELDS, label)

    return ServiceDefinition(
        name=data["name"],
        container=data.get("container") or None,
        icon=data.get("icon") or None,
        href=data.get("href") or None,
        description=data.get("description") or None,
    )


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
