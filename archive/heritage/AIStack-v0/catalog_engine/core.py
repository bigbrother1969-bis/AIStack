from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class CatalogItem:
    id: str
    label: str
    kind: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Catalog:
    catalog_id: str
    title: str
    items: list[CatalogItem]
    metadata: dict[str, Any] = field(default_factory=dict)


class CatalogProvider(Protocol):
    provider_id: str

    def collect(self) -> Catalog:
        ...
