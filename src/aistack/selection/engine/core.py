from __future__ import annotations

from aistack.catalog.views import CatalogView
from aistack.selection.core import Selection
from aistack.selection.strategies import SelectionStrategy


class SelectionEngine:
    """Generic selection engine working from Catalog Views and Selection Strategies."""

    def select(
        self,
        view: CatalogView,
        selection_id: str,
        strategy: SelectionStrategy,
        metadata: dict[str, str] | None = None,
    ) -> Selection:
        selected = strategy.select(view)

        return Selection(
            selection_id=selection_id,
            catalog_id=view.source_catalog_id,
            selected_ids=selected,
            metadata={
                "source_view": view.view_id,
                **(metadata or {}),
            },
        )
