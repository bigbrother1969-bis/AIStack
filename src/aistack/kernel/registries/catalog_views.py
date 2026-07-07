from __future__ import annotations

from aistack.catalog.views import CatalogViewEngine
from aistack.kernel.registry import Registry


class CatalogViewRegistry(Registry[CatalogViewEngine]):
    """Registry of Catalog View Engines."""

    pass
