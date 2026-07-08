from __future__ import annotations

from typing import Any

from aistack.kernel.catalog import Catalog, CatalogItem


class ComposeRuntimeCatalogBuilder:
    """Build a governed catalog from Docker Compose observations."""

    def build(self, observation: dict[str, Any]) -> Catalog:
        projects = observation["compose"]["projects"]

        return Catalog(
            catalog_id="compose-runtime",
            title="Docker Compose Runtime Catalog",
            metadata={
                "source_provider": observation["provider"]["id"],
                "collected_at": observation["collected_at"],
            },
            items=[
                CatalogItem(
                    id=project["name"],
                    label=project["name"],
                    kind="compose-project",
                    source=project.get("working_dir") or "",
                    metadata={
                        "working_dir": project.get("working_dir") or "",
                        "config_files": project.get("config_files") or "",
                        "service_count": str(len(project.get("services", {}))),
                    },
                )
                for project in projects
            ],
        )
