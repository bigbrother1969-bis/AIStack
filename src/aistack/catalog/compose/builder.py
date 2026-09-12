from __future__ import annotations

from typing import Any

from aistack.kernel.catalog import Catalog, CatalogItem


class ComposeRuntimeCatalogBuilder:
    """Build a governed catalog from Docker Compose observations.

    **Keeps the project's own membership, not only its count.**
    Until 2026-09-10 this builder reduced `project["services"]` —
    the container names `ComposeProvider.collect()` already
    resolves, one per service — to `service_count`, a number. The
    raw observation always carried the edge a knowledge graph of
    the infrastructure needs (which containers belong to which
    project); this builder discarded it before it ever reached a
    governed `Catalog`. Named while scoping `PLAN-TRAJECTOIRE-
    2026-09-04` jalon J2 — rendering the reconstructed
    `architecture.html` groups containers by their Compose
    project, which this gap made impossible to do from the
    Catalog alone.

    **Sorted, not passed through in insertion order.** A `dict`
    iterates in the order its keys were first set, which for
    `project["services"]` is the order `docker ps` listed
    containers in — the same instability `DockerRuntimeCatalogBuilder`
    already sorts `mounts` and `images` against (`ARC-P-006`: this
    family showed it, so only this family is sorted).

    **`items` is a tuple, matching what `Catalog` declares.** Until
    2026-09-10 this method built it as a list comprehension —
    `Catalog.items: tuple[CatalogItem, ...]` accepted it without
    complaint at runtime, since a dataclass field's declared type is
    not enforced, but `mypy` named the mismatch on its first run
    against this codebase.

    **`dependency_edges`, added 2026-09-12** (`claude/PLAN-J11-
    CONSOLE-2026-09-11.md` §10, third gap) — `ComposeProvider` now
    reads each service's own `depends_on:` from the real compose
    file, naming *service* names; this builder is where those become
    *container*-to-container edges, the same boundary it already
    keeps for `containers` (service → container_name). An edge
    survives only when both ends resolve to a container this same
    project actually observed — a `depends_on` naming a service that
    is not (or no longer) running is not asserted as an edge to a
    node nothing here has ever seen (`ARC-P-012`).
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
