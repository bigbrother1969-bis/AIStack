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

    # This engine has no configuration, so one instance serves every
    # caller; `MediaLibraryProvider` is configured per application and
    # is built per use instead of registered.
    kernel.registries.catalog_views.register(
        MediaTreeViewEngine.view_id,
        MediaTreeViewEngine(),
    )
