from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from aistack.kernel.catalog import Catalog


@dataclass(frozen=True)
class CatalogViewItem:
    id: str
    label: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CatalogView:
    view_id: str
    source_catalog_id: str
    title: str
    items: list[CatalogViewItem]
    metadata: dict[str, str] = field(default_factory=dict)
