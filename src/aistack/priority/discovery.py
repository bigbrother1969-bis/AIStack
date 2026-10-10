from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiscoveredContainer:
    """
    One container Docker reports, shaped for the `priority_ui` screen.

    Carries no CPU value: a discovered container is not yet classified.
    """

    name: str
    image: str
    running: bool
    status: str


def resolve_discovered_containers(
    observation: Mapping[str, Any],
) -> tuple[DiscoveredContainer, ...]:
    """
    Shape `DockerProvider`'s raw `docker ps -a` observation into the
    containers a human can classify, sorted by name.

    Stopped containers are kept (`running` tells them apart). Entries with
    no name are dropped.
    """

    docker = observation.get("docker") or {}
    entries = docker.get("containers") or []

    discovered = [
        DiscoveredContainer(
            name=name,
            image=str(entry.get("Image", "")),
            running=(entry.get("State") == "running"),
            status=str(entry.get("Status", "")),
        )
        for entry in entries
        if (name := _first_name(entry.get("Names", "")))
    ]

    return tuple(sorted(discovered, key=lambda container: container.name))


def _first_name(names: Any) -> str:
    """
    Return the primary name from Docker's comma-separated `Names` field.
    """

    return str(names).split(",")[0].strip()
