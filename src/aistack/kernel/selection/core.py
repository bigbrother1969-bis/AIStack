from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Selection:
    """Governed selection produced from a catalog."""

    selection_id: str
    catalog_id: str
    selected_ids: list[str]
    metadata: dict[str, str] = field(default_factory=dict)
