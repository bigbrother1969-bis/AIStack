from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SelectionItem:
    id: str
    label: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SelectionCatalog:
    catalog_id: str
    title: str
    items: list[SelectionItem]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Selection:
    selection_id: str
    catalog_id: str
    selected_ids: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)
