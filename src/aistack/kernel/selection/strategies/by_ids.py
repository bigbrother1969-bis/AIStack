from __future__ import annotations

from collections.abc import Iterable

from aistack.kernel.catalog.views import CatalogView


class ByIdsSelectionStrategy:
    """Select items from a Catalog View using explicit identifiers."""

    def __init__(self, selected_ids: Iterable[str]) -> None:
        self.selected_ids = list(selected_ids)

    def select(self, view: CatalogView) -> list[str]:
        available_ids = {item.id for item in view.items}
        return sorted(item_id for item_id in self.selected_ids if item_id in available_ids)
