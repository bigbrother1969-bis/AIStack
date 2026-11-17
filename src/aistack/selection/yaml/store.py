from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import yaml

from aistack.kernel.selection import Selection


def render_selection_yaml(selection: Selection) -> str:
    """A governed selection as YAML text. Writing it is `aistack.declaration`'s job."""
    return yaml.safe_dump(asdict(selection), sort_keys=False, allow_unicode=True)


def load_selection_yaml(path: Path) -> Selection | None:
    """Load a governed selection from YAML."""
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(f"Selection YAML must contain a mapping: {path}")

    return Selection(
        selection_id=data["selection_id"],
        catalog_id=data["catalog_id"],
        selected_ids=data.get("selected_ids", []),
        metadata=data.get("metadata", {}),
    )
