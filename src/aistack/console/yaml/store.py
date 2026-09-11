from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.contracts.console_link import ConsoleLink

_REQUIRED_LINK_FIELDS = ("name", "description", "url")


def load_console_links_yaml(path: Path) -> tuple[ConsoleLink, ...]:
    """
    Load `PLAN-J11`'s declared console links from YAML.

    Mirrors `load_health_score_weights_yaml` field for field (written
    by hand, read-only, a missing key names which one and where) and
    in shape: one flat list, no per-host wrapper — a `ConsoleLink`'s
    `url` already carries whatever host-specific fact it names
    (`GIGABYTE:8181`, a relative `/health.html`), so there is nothing
    left for this loader itself to scope by host.
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise ValueError(
                f"console link definition {path} is not valid YAML: {error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(f"console link definition must contain a mapping: {path}")

    if "links" not in data:
        raise ValueError(f"console link definition {path} is missing: links")

    links_data = data["links"]

    if not isinstance(links_data, list):
        raise ValueError(f"console link definition {path}: links must be a list")

    return tuple(
        _load_link(item, path, index) for index, item in enumerate(links_data)
    )


def _load_link(data: Any, path: Path, index: int) -> ConsoleLink:
    label = f"console link definition {path}: links[{index}]"

    if not isinstance(data, dict):
        raise ValueError(f"{label} must be a mapping")

    missing = [field for field in _REQUIRED_LINK_FIELDS if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")

    return ConsoleLink(
        name=data["name"],
        description=data["description"],
        url=data["url"],
    )
