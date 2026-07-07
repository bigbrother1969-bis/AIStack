from __future__ import annotations

from aistack.kernel.catalog import Catalog
from aistack.catalog.views.core import CatalogView, CatalogViewItem


class MusicSelectionViewEngine:
    """Build a selection-oriented view from a music catalog."""

    def build(self, catalog: Catalog) -> CatalogView:
        return CatalogView(
            view_id="music-selection",
            source_catalog_id=catalog.catalog_id,
            title=f"{catalog.title} Selection View",
            items=[
                CatalogViewItem(
                    id=item.id,
                    label=item.label,
                    metadata={
                        "kind": item.kind,
                        "source": item.source,
                        **item.metadata,
                    },
                )
                for item in catalog.items
            ],
            metadata={
                "purpose": "selection",
                "domain": "music",
            },
        )
