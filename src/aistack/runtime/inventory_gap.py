from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from aistack.architecture.definition import ServiceCategorizationDefinition
from aistack.contracts.inventory_gap import (
    DECLARED_UNDISCOVERED,
    DISCOVERED_UNDECLARED,
    InventoryGap,
)


def find_inventory_gaps(
    categorization: ServiceCategorizationDefinition,
    discovered: Mapping[str, str | None],
) -> tuple[InventoryGap, ...]:
    """
    Compare the containers declared in `service_categorization.yml` with
    the containers found running.

    `discovered` maps a container identity to the host it was found on
    (`None` for local). Returns DISCOVERED_UNDECLARED gaps, then
    DECLARED_UNDISCOVERED gaps, each sorted by container name. Services
    with no container are ignored. A service declared `on_demand` is never
    reported as undiscovered, since being absent is its normal state.
    """

    declared: dict[str, str] = {}
    on_demand: set[str] = set()

    for category in categorization.categories:
        for service in category.services:
            if service.container is not None:
                declared[service.container] = service.name
                if service.on_demand:
                    on_demand.add(service.container)

    gaps: list[InventoryGap] = []

    for container in sorted(discovered):
        if container not in declared:
            gaps.append(
                InventoryGap(
                    kind=DISCOVERED_UNDECLARED,
                    container=container,
                    host=discovered[container],
                )
            )

    for container in sorted(declared):
        if container not in discovered and container not in on_demand:
            gaps.append(
                InventoryGap(
                    kind=DECLARED_UNDISCOVERED,
                    container=container,
                    service=declared[container],
                )
            )

    return tuple(gaps)


def discovered_containers_from_network_observation(
    observation: Mapping[str, Any],
) -> dict[str, str]:
    """
    Map every container in the last network-docker observation
    (`network_docker.hosts[].containers[]`) to the host that reported it.

    The identity is `Names`, else `Name`, else `ID`, as in
    `DockerRuntimeCatalogBuilder._identity`. Containers with none of these,
    and host entries without `host`, are skipped.
    """

    containers: dict[str, str] = {}

    for host_entry in observation.get("network_docker", {}).get("hosts", []):
        host = host_entry.get("host")

        if not host:
            continue

        for item in host_entry.get("containers", []):
            identity = item.get("Names") or item.get("Name") or item.get("ID")

            if identity:
                containers[identity] = host

    return containers
