from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import yaml

from aistack.kernel.catalog import Catalog, CatalogItem


def load_catalog_yaml(path: Path) -> Catalog:
    """
    Load a governed catalog from YAML.

    **`items` is a tuple, matching what `Catalog` declares.** Until
    2026-09-10 this built it as a list comprehension —
    `Catalog.items: tuple[CatalogItem, ...]` accepted it without
    complaint at runtime, since a dataclass field's declared type is
    not enforced, but `mypy` named the mismatch on its first run
    against this codebase.
    """
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"Catalog YAML must contain a mapping: {path}")
    return Catalog(
        catalog_id=data["catalog_id"],
        title=data["title"],
        metadata=data.get("metadata", {}),
        items=tuple(
            CatalogItem(
                id=item["id"],
                label=item.get("label", item["id"]),
                kind=item.get("kind", ""),
                source=item.get("source", ""),
                metadata=item.get("metadata", {}),
            )
            for item in data.get("items", [])
        ),
    )


def save_catalog_yaml(catalog: Catalog, path: Path) -> Path:
    """Save a governed catalog to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(asdict(catalog), stream, sort_keys=False, allow_unicode=True)
    return path
