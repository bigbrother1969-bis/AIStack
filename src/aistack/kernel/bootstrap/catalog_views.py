from __future__ import annotations

from aistack.catalog.views.music import MusicSelectionViewEngine
from aistack.kernel import Kernel


def register_default_catalog_views(kernel: Kernel) -> None:
    """Register default Catalog View Engines into the Kernel."""

    kernel.registries.catalog_views.register(
        "music-selection",
        MusicSelectionViewEngine(),
    )
