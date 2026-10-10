from __future__ import annotations

from typing import Any

from aistack.kernel.catalog import Catalog, CatalogItem


class ComposeRuntimeCatalogBuilder:
    """Build a catalog of Compose projects from Docker Compose observations.

    Each project keeps its member containers and its `depends_on` edges,
    translated from service names to container names. An edge is kept only
    when both ends are observed containers. Both lists are sorted, since
    `docker ps` order is not stable.
    """

    def build(self, observation: dict[str, Any]) -> Catalog:
        projects = observation["compose"]["projects"]

        return Catalog(
            catalog_id="compose-runtime",
            title="Docker Compose Runtime Catalog",
            metadata={
                "source_provider": observation["provider"]["id"],
                "collected_at": observation["collected_at"],
            },
            items=tuple(
                CatalogItem(
                    id=project["name"],
                    label=project["name"],
                    kind="compose-project",
                    source=project.get("working_dir") or "",
                    metadata={
                        "working_dir": project.get("working_dir") or "",
                        "config_files": project.get("config_files") or "",
                        "service_count": str(len(project.get("services", {}))),
                        "containers": self._sorted_containers(
                            project.get("services", {})
                        ),
                        "dependency_edges": self._sorted_dependency_edges(
                            project.get("services", {})
                        ),
                    },
                )
                for project in projects
            ),
        )

    def _sorted_containers(self, services: dict[str, Any]) -> str:
        names = {
            str(service["container_name"])
            for service in services.values()
            if service.get("container_name")
        }
        return ",".join(sorted(names))

    def _sorted_dependency_edges(self, services: dict[str, Any]) -> str:
        container_by_service = {
            service_name: str(service["container_name"])
            for service_name, service in services.items()
            if service.get("container_name")
        }

        edges: set[tuple[str, str]] = set()

        for service_name, service in services.items():
            from_container = container_by_service.get(service_name)
            if not from_container:
                continue

            for target_service in service.get("depends_on") or ():
                to_container = container_by_service.get(target_service)
                if to_container:
                    edges.add((from_container, to_container))

        return ",".join(f"{source}->{target}" for source, target in sorted(edges))
