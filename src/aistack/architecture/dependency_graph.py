from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.catalog import Catalog


@dataclass(frozen=True)
class ContainerDependencyEdge:
    """
    One `depends_on:` relationship, already resolved to the two
    container names it names — never the two Compose *service* names
    it was declared with (`ComposeRuntimeCatalogBuilder` is where that
    resolution happens; this dataclass only carries the result).
    """

    from_container: str
    to_container: str


@dataclass(frozen=True)
class ComposeProjectDependencies:
    """
    One Compose project's real dependency picture.

    **`containers` is every container this project observed running,
    not only the ones named by an edge.** Decided with the owner
    2026-09-12: most of the real `depends_on` edges GIGABYTE's own
    files declare point at sidecar containers (a project's own `_db`,
    `redis`, or `gluetun`) that `service_categorization.yml` does not
    curate as services of their own — restricting this graph to
    already-declared services would leave almost nothing to draw an
    edge to. So a project's full, real container membership is the
    node set; `service_categorization.yml`'s own curation is what the
    *other* views in this page already show.
    """

    project: str
    containers: tuple[str, ...] = ()
    edges: tuple[ContainerDependencyEdge, ...] = ()


@dataclass(frozen=True)
class DependencyGraph:
    """
    Every Compose project that declares at least one real dependency
    — never all of them. A project with no `depends_on:` anywhere in
    its compose file (most of GIGABYTE's 33 projects, confirmed
    2026-09-12) has nothing this graph exists to show; the same
    "nothing observed, nothing rendered" rule the topology and Beszel
    sections already follow, so `render_dependency_mermaid` never
    draws an isolated, edge-less subgraph purely for the sake of
    completeness.
    """

    projects: tuple[ComposeProjectDependencies, ...] = ()


def build_dependency_graph(compose_catalog: Catalog) -> DependencyGraph:
    """
    Read `ComposeRuntimeCatalogBuilder`'s own `dependency_edges`/
    `containers` metadata off each compose-project `CatalogItem` and
    turn it into a typed, deterministic `DependencyGraph`.

    **Tolerant, not strict** — same reasoning as
    `build_beszel_readings`: this reads a governed `Catalog`, not a
    hand-written file a typo in is the owner's own mistake to fix, so
    a missing or oddly-shaped `dependency_edges` value degrades to
    "this project has no edges" rather than raising.

    **Sorted by project name.** `Catalog.items`' own order follows
    whichever order `docker ps` first listed a project's containers
    in — the same instability `ComposeRuntimeCatalogBuilder` already
    sorts `containers`/`dependency_edges` against internally; the
    project-level order this function returns needed the same
    treatment, since nothing upstream of this function ever sorts it.
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
