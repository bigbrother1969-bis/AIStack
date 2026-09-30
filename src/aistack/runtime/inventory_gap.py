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
    Join `service_categorization.yml`'s own declared containers against
    every container actually found running — 1.6 tranche 3 (R9,
    2026-09-30).

    **`discovered` is already assembled by the caller** — a container
    identity mapped to the host it was found on (`None` for local,
    the same convention `InventoryGap.host` documents). This function
    never collects anything itself and never touches the network or a
    live `docker` binary — it is pure, the same discipline
    `find_backup_gaps`/`find_uncovered_state` already hold: readings
    already collected in, gaps out.

    **A declared service naming no container (`ServiceDefinition.
    container is None`) is silently excluded from both directions** —
    the same exclusion `build_architecture_graph`'s own
    `ServiceStatus.NO_CONTAINER` already makes: hardware AIStack has no
    provider for, or a service reached without being a container of
    its own. There is nothing to reconcile for it.

    **Two passes, not one join** — every discovered container not
    declared anywhere becomes a `DISCOVERED_UNDECLARED` gap; every
    declared container not found anywhere becomes a `DECLARED_
    UNDISCOVERED` gap. Sorted by container name in each pass, for a
    stable, reviewable order independent of dict iteration or which
    host answered first.
    """

    declared: dict[str, str] = {}

    for category in categorization.categories:
        for service in category.services:
            if service.container is not None:
                declared[service.container] = service.name

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
        if container not in discovered:
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
    Every container `network_docker_discover`'s last observation found
    on a host other than this one, mapped to the host that reported it
    — `reports/generated/network-docker-observation.json`'s own shape
    (`NetworkDockerDiscoveryProvider.collect()`:
    `network_docker.hosts[].containers[]`, one raw `docker ps -a
    --format '{{json .}}'` line per container).

    **`Names` falling back to `Name` then `ID`, exactly
    `DockerRuntimeCatalogBuilder._identity`'s own convention** —
    mirrored here rather than imported, since that builder expects a
    full `DockerProvider.collect()` shape (`docker.containers/images/
    networks/volumes`) this per-host, containers-only observation does
    not carry. A container missing all three identities is silently
    skipped, never assigned a placeholder identity — the same
    "nothing dropped, nothing invented" discipline `_identity` itself
    documents, applied here to the one case it cannot reach: a
    container this function cannot name at all.

    A host entry naming no `host`, or naming containers under a key
    absent entirely, contributes nothing — the same tolerant reading
    `NetworkDockerDiscoveryProvider` itself already holds for absent
    `nmap`/`ssh`: nothing observed, nothing raised.
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
