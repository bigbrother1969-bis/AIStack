from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aistack.architecture.definition import ServiceCategorizationDefinition
from aistack.kernel.catalog import Catalog


class ServiceStatus(Enum):
    """
    What the Docker and Compose catalogs can say about a categorized
    service. Checked in this order:

    - `IN_COMPOSE_PROJECT`: its container belongs to an observed Compose
      project (running or stopped).
    - `OBSERVED`: the Docker catalog has the container, but no tracked
      Compose project claims it.
    - `DECLARED_NOT_OBSERVED`: neither catalog has seen the container,
      typically a service on a host without a Docker provider.
    - `NO_CONTAINER`: the categorization names no container.
    """

    IN_COMPOSE_PROJECT = "in_compose_project"
    OBSERVED = "observed"
    DECLARED_NOT_OBSERVED = "declared_not_observed"
    NO_CONTAINER = "no_container"


@dataclass(frozen=True)
class ServiceNode:
    """
    One categorized service, joined against what the catalogs observed.

    `compose_project` is set only for `IN_COMPOSE_PROJECT`.
    `icon`/`href`/`description` pass through from `ServiceDefinition`.
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
    """One category and its service nodes; the unit views filter on."""

    name: str
    services: tuple[ServiceNode, ...] = ()


@dataclass(frozen=True)
class ArchitectureGraph:
    """
    The whole homelab, classified, as data rather than Mermaid text, so it can
    be tested on its own; rendering to `.mmd` and HTML happens later.
    """

    categories: tuple[CategoryGraph, ...] = ()


def build_architecture_graph(
    categorization: ServiceCategorizationDefinition,
    docker_catalog: Catalog,
    compose_catalog: Catalog,
) -> ArchitectureGraph:
    """
    Join the declared categorization against the observed catalogs.

    `docker_catalog` comes from `DockerRuntimeCatalogBuilder` (container
    items keyed by name); `compose_catalog` comes from
    `ComposeRuntimeCatalogBuilder` (project items with a `containers`
    metadata field).
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
