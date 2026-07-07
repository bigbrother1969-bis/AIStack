from __future__ import annotations

from typing import Any

from aistack.kernel.selection import SelectionCatalog, SelectionItem


class DockerSelectionCatalogBuilder:
    """Build a selectable catalog view from the Docker runtime catalog."""

    def build(self, docker_catalog: dict[str, Any]) -> SelectionCatalog:
        containers = docker_catalog["infrastructure_assets"]["containers"]

        return SelectionCatalog(
            catalog_id="docker-runtime-containers",
            title="Docker Runtime Containers",
            items=[
                SelectionItem(
                    id=container["name"],
                    label=container["name"],
                    metadata={
                        "image": container.get("image") or "",
                        "state": container.get("state") or "",
                        "status": container.get("status") or "",
                    },
                )
                for container in containers
                if container.get("name")
            ],
            metadata={
                "source_catalog": docker_catalog["catalog_type"],
                "source_provider": docker_catalog["source_provider"],
            },
        )
