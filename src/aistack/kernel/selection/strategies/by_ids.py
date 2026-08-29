from __future__ import annotations

from collections.abc import Iterable

from aistack.kernel.catalog.views import CatalogView


class ByIdsSelectionStrategy:
    """Select items from a Catalog View using explicit identifiers."""

    def __init__(self, selected_ids: Iterable[str]) -> None:
        self.selected_ids = list(selected_ids)

    def select(self, view: CatalogView) -> tuple[str, ...]:
        """
        Returned `list[str]` until 2026-08-29 while the Protocol
        declared `tuple[str, ...]`.

        ADR-0003 recorded the divergence as an observation on
        2026-08-27 and left it: nothing consumed the chain, so
        nothing could be wrong. It became live the day the
        Selection UI started calling the engine, and neither
        `contract-debt` nor `false-declarations` sees it —
        both compare call shapes, not return types.
        """

        available_ids = {item.id for item in view.items}

        return tuple(
            sorted(
                item_id
                for item_id in self.selected_ids
                if item_id in available_ids
            )
        )
