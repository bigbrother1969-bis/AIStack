from __future__ import annotations

from aistack.kernel.catalog import Catalog
from aistack.kernel.catalog.views import CatalogView, CatalogViewItem


class DockerContainerViewEngine:
    """
    Build a selection-oriented view of the containers of a Docker
    runtime catalog.

    **This is the producer ADR-0002 decided and nothing
    implemented.** Until 2026-08-29 the live Docker path built a
    `SelectionCatalog` — a v0 type carrying no view identity, no
    link back to its catalog, and satisfying no contract — while
    `CatalogViewEngine` was satisfied only by a music engine
    nothing retrieved. GOV-0002/OS-042, qualified 2026-08-29:
    `CatalogView` is the Catalog View.

    **It filters on `kind`, and that is the whole reason the
    filter exists.** The runtime catalog holds four families in
    one flat list; identifiers are unique within a family and not
    across them. A view holds one family, so within a view an
    identifier is unambiguous and a Selection Strategy can select
    by it.
    """

    KIND = "container"

    def build(self, catalog: Catalog) -> CatalogView:
        containers = [item for item in catalog.items if item.kind == self.KIND]

        return CatalogView(
            view_id="docker-containers",
            source_catalog_id=catalog.catalog_id,
            title=f"{catalog.title} — Containers",
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
                for item in containers
            ],
            metadata={
                "purpose": "selection",
                "domain": "docker",
                "kind": self.KIND,
            },
        )
