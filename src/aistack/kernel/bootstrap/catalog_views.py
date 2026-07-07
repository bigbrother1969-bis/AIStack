from __future__ import annotations

from aistack.catalog.views.music import MusicSelectionViewEngine
from aistack.kernel.context import KernelContext


def register_default_catalog_views(ctx: KernelContext) -> None:
    """Register default Catalog View Engines into the Kernel Context."""

    ctx.catalog_views.register("music-selection", MusicSelectionViewEngine())
