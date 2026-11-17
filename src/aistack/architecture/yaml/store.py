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
    Load the service categorization from YAML.

    The file is edited by hand, or by one click on the screen *Nouveautés*
    (`aistack.arrivals.declare`, which adds a service as text and keeps a
    dated copy); a missing key raises a `ValueError` naming it and its
    location.
    """

    return parse_service_categorization_yaml(path.read_text(encoding="utf-8"), path)


def parse_service_categorization_yaml(text: str, path: Path) -> ServiceCategorizationDefinition:
    """The same, from the text; `path` names the file in the messages."""

    data = yaml.safe_load(text)

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
        on_demand=_on_demand(data.get("on_demand", False), label),
    )


def _on_demand(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{label}: on_demand must be true or false")
    return value


def _require(data: dict, fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
