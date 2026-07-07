from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CatalogItem:
    id: str
    label: str
    kind: str = ""
    source: str = ""
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Catalog:
    catalog_id: str
    title: str
    items: list[CatalogItem]
    metadata: dict[str, str] = field(default_factory=dict)
