from __future__ import annotations

from typing import Protocol

from aistack.kernel.catalog import Catalog
from aistack.kernel.catalog.views import CatalogView


class CatalogViewEngine(Protocol):
    """Build a purpose-specific view from a governed catalog."""

    def build(self, catalog: Catalog) -> CatalogView:
        ...
