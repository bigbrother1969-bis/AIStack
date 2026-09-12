from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aistack.architecture.definition import ServiceCategorizationDefinition
from aistack.kernel.catalog import Catalog


class ServiceStatus(Enum):
    """
    What AIStack's own catalogs can say about one categorized service.

    **Four states, checked in this order, not three.** The old
    system's RPI/GIGA/VPN split (`claude/PLAN-J2-ARCHITECTURE-HTML-
    2026-09-10.md`, "Une réduction de périmètre assumée") is not
    reconstructed — AIStack has no provider for a Raspberry Pi's own
    Docker or compose files. What it does have is two catalogs, and
    the honest thing they can say about a service is only ever one of
    these:

    - `IN_COMPOSE_PROJECT` — its container belongs to a project the
      Compose Catalog observed. Checked first: a project's own
      `docker-compose.yml` naming this container is a stronger fact
      than `docker ps` alone, and settles the question even if the
      container happens to be stopped when the Docker Catalog was
      built (`docker ps -a` — `DockerRuntimeCatalogBuilder` observes
      stopped containers too, so this is about project membership,
      not liveness).
    - `OBSERVED` — no compose project claims it, but the Docker
      Catalog has it directly (a container run by hand, or a compose
      project this repository does not track).
    - `DECLARED_NOT_OBSERVED` — the categorization names a container
      neither catalog has ever seen. Most often the Raspberry Pi's own
      services (Pi-hole, Uptime Kuma, Homepage, NPM itself) — real,
      but outside what AIStack's one Docker provider (GIGABYTE) can
      observe.
    - `NO_CONTAINER` — the categorization itself names no container at
      all (`ServiceDefinition.container is None`) — hardware AIStack
      has no provider for (the Freebox), or a service reached without
      being a container of its own (Architecture Homelab, Indy, Music
      Sync). There is nothing to look up.
    """

    IN_COMPOSE_PROJECT = "in_compose_project"
    OBSERVED = "observed"
    DECLARED_NOT_OBSERVED = "declared_not_observed"
    NO_CONTAINER = "no_container"


@dataclass(frozen=True)
class ServiceNode:
    """
    One categorized service, joined against what the catalogs observed.

    **`compose_project` is set only for `ServiceStatus.IN_COMPOSE_PROJECT`**
    — every other status has nothing to name here, so it stays `None`
    rather than being pressed into meaning something else (an empty
    string would still need a caller to know which status makes it
    meaningful).

    **`icon`/`href`/`description` carry straight from `ServiceDefinition`,
    unexamined** (added 2026-09-12, `claude/PLAN-J11-CONSOLE-2026-09-11.md`
    §10) — unlike `container`, nothing here joins them against a catalog:
    there is no "observed href", only a declared one, so this is a plain
    pass-through rather than a status computation like the rest of this
    function.
    """

    name: str
    category: str
    container: str | None
    status: ServiceStatus
    compose_project: str | None = None
    icon: str | None = None
    href: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class CategoryGraph:
    """
    One category and the service nodes placed in it.

    The unit step 4's per-category views (`generate_mermaid_views.py`'s
    own transformation, generalized) filter `ArchitectureGraph.categories`
    on.
    """

    name: str
    services: tuple[ServiceNode, ...] = ()


@dataclass(frozen=True)
class ArchitectureGraph:
    """
    The whole homelab, classified — not yet Mermaid.

    **Structured, not textual.** `generate_mermaid.py` wrote `.mmd`
    text directly from `services.yaml` and the compose files it
    parsed; this builder stops one step short of that, the same way
    the Kernel Runtime separates `generate` from `render`
    (`docs/99-meta/roadmap/Kernel-Runtime-Roadmap.md`). What this
    builds is testable on its own — "is Jellyfin's status
    `IN_COMPOSE_PROJECT`" is an assertion about data, not about
    Mermaid syntax — and step 5
    (`claude/PLAN-J2-ARCHITECTURE-HTML-2026-09-10.md`) is what turns
    it into `.mmd` text and wraps it in HTML.
    """

    categories: tuple[CategoryGraph, ...] = ()


def build_architecture_graph(
    categorization: ServiceCategorizationDefinition,
    docker_catalog: Catalog,
    compose_catalog: Catalog,
) -> ArchitectureGraph:
    """
    Join the declared categorization against what GIGABYTE's own
    catalogs observed.

    **Reads two catalogs shaped by their own builders, not raw
    observations.** `docker_catalog` is `DockerRuntimeCatalogBuilder`'s
    output (container items, `id` the container's own name —
    `_identity`'s own `Names`/`Name`/`ID` fallback); `compose_catalog`
    is `ComposeRuntimeCatalogBuilder`'s (compose-project items, each
    carrying a `containers` metadata field —
    `PLAN-TRAJECTOIRE-2026-09-04` J2's own step 1, without which this
    function could not tell a service's Compose project at all).
    """

    observed_containers = {
        item.id for item in docker_catalog.items if item.kind == "container"
    }

    container_to_project: dict[str, str] = {}
    for project in compose_catalog.items:
        containers = project.metadata.get("containers") or ""
        for name in containers.split(","):
            name = name.strip()
            if name:
                container_to_project[name] = project.id

    return ArchitectureGraph(
        categories=tuple(
            CategoryGraph(
                name=category.name,
                services=tuple(
                    _service_node(
                        service.name,
                        category.name,
                        service.container,
                        observed_containers,
                        container_to_project,
                        service.icon,
                        service.href,
                        service.description,
                    )
                    for service in category.services
                ),
            )
            for category in categorization.categories
        )
    )


def _service_node(
    name: str,
    category: str,
    container: str | None,
    observed_containers: set[str],
    container_to_project: dict[str, str],
    icon: str | None = None,
    href: str | None = None,
    description: str | None = None,
) -> ServiceNode:
    if container is None:
        return ServiceNode(
            name=name,
            category=category,
            container=None,
            status=ServiceStatus.NO_CONTAINER,
            icon=icon,
            href=href,
            description=description,
        )

    if container in container_to_project:
        return ServiceNode(
            name=name,
            category=category,
            container=container,
            status=ServiceStatus.IN_COMPOSE_PROJECT,
            compose_project=container_to_project[container],
            icon=icon,
            href=href,
            description=description,
        )

    if container in observed_containers:
        return ServiceNode(
            name=name,
            category=category,
            container=container,
            status=ServiceStatus.OBSERVED,
            icon=icon,
            href=href,
            description=description,
        )

    return ServiceNode(
        name=name,
        category=category,
        container=container,
        status=ServiceStatus.DECLARED_NOT_OBSERVED,
        icon=icon,
        href=href,
        description=description,
    )
