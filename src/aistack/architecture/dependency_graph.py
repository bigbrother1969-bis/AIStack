from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.catalog import Catalog


@dataclass(frozen=True)
class ContainerDependencyEdge:
    """
    One `depends_on:` relationship, resolved to container names (not
    Compose service names) by `ComposeRuntimeCatalogBuilder`.
    """

    from_container: str
    to_container: str


@dataclass(frozen=True)
class ComposeProjectDependencies:
    """
    One Compose project's dependency picture.

    `containers` lists every container of the project, not only those on
    an edge: most real edges point at sidecars (databases, redis, VPN) that
    the service categorization does not list.
    """

    project: str
    containers: tuple[str, ...] = ()
    edges: tuple[ContainerDependencyEdge, ...] = ()


@dataclass(frozen=True)
class DependencyGraph:
    """
    The Compose projects that declare at least one dependency; projects with
    no `depends_on:` are left out.
    """

    projects: tuple[ComposeProjectDependencies, ...] = ()


def build_dependency_graph(compose_catalog: Catalog) -> DependencyGraph:
    """
    Build a `DependencyGraph` from the `dependency_edges`/`containers`
    metadata of each compose-project catalog item, sorted by project name.

    Tolerant: a missing or malformed `dependency_edges` means no edges.
    """

    projects: list[ComposeProjectDependencies] = []

    for item in compose_catalog.items:
        if item.kind != "compose-project":
            continue

        edges = _parse_edges(item.metadata.get("dependency_edges") or "")

        if not edges:
            continue

        containers = _parse_containers(item.metadata.get("containers") or "")

        projects.append(
            ComposeProjectDependencies(
                project=item.id,
                containers=containers,
                edges=edges,
            )
        )

    projects.sort(key=lambda project: project.project)

    return DependencyGraph(projects=tuple(projects))


def _parse_edges(raw: str) -> tuple[ContainerDependencyEdge, ...]:
    edges: list[ContainerDependencyEdge] = []

    for chunk in raw.split(","):
        chunk = chunk.strip()

        if not chunk or "->" not in chunk:
            continue

        from_container, _, to_container = chunk.partition("->")
        from_container = from_container.strip()
        to_container = to_container.strip()

        if from_container and to_container:
            edges.append(ContainerDependencyEdge(from_container, to_container))

    return tuple(edges)


def _parse_containers(raw: str) -> tuple[str, ...]:
    return tuple(name.strip() for name in raw.split(",") if name.strip())
