from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SelectionItem:
    """Selectable item derived from a governed catalog."""

    id: str
    label: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SelectionCatalog:
    """Catalog view exposed to a selection workflow."""

    catalog_id: str
    title: str
    items: list[SelectionItem]
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Selection:
    """Governed selection produced from a catalog."""

    selection_id: str
    catalog_id: str
    selected_ids: list[str]
    metadata: dict[str, str] = field(default_factory=dict)
