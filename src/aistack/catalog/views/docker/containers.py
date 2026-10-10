from __future__ import annotations

from aistack.kernel.catalog import Catalog
from aistack.kernel.catalog.views import CatalogView, CatalogViewItem


class DockerContainerViewEngine:
    """Build a selection-oriented view of the containers of a Docker
    runtime catalog (`ADR-0002`).

    It filters on `kind` because the runtime catalog mixes four families
    whose identifiers are unique only within a family; a single-family view
    lets a Selection Strategy select by identifier.
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
