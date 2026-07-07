from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import yaml

from aistack.catalog.core import Catalog, CatalogItem


def load_catalog_yaml(path: Path) -> Catalog:
    """Load a governed catalog from YAML."""
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"Catalog YAML must contain a mapping: {path}")
    return Catalog(
        catalog_id=data["catalog_id"],
        title=data["title"],
        metadata=data.get("metadata", {}),
        items=[
            CatalogItem(
                id=item["id"],
                label=item.get("label", item["id"]),
                kind=item.get("kind", ""),
                source=item.get("source", ""),
                metadata=item.get("metadata", {}),
            )
            for item in data.get("items", [])
        ],
    )


def save_catalog_yaml(catalog: Catalog, path: Path) -> Path:
    """Save a governed catalog to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(asdict(catalog), stream, sort_keys=False, allow_unicode=True)
    return path
