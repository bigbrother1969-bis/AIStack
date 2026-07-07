from __future__ import annotations

from typing import Protocol

from aistack.catalog.views import CatalogView


class SelectionStrategy(Protocol):
    """Select item identifiers from a Catalog View."""

    def select(self, view: CatalogView) -> list[str]:
        ...
