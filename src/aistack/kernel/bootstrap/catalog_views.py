from __future__ import annotations

from aistack.catalog.views.docker import DockerContainerViewEngine
from aistack.catalog.views.media import MediaTreeViewEngine
from aistack.catalog.views.music import MusicSelectionViewEngine
from aistack.kernel import Kernel


def register_default_catalog_views(kernel: Kernel) -> None:
    """Register default Catalog View Engines into the Kernel."""

    kernel.registries.catalog_views.register(
        "music-selection",
        MusicSelectionViewEngine(),
    )

    kernel.registries.catalog_views.register(
        "docker-containers",
        DockerContainerViewEngine(),
    )

    # Registered, where `MediaLibraryProvider` is not, and the
    # difference is the one the `by-ids` removal drew on
    # 2026-08-29: this engine carries no configuration, so a
    # single instance serves every caller. The provider carries a
    # root and a list of extensions, which travel in the
    # application definition, so it is constructed per use.
    kernel.registries.catalog_views.register(
        MediaTreeViewEngine.view_id,
        MediaTreeViewEngine(),
    )
