from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DiscoveredContainer:
    """
    One container Docker currently reports, shaped for a human to
    read and choose from — `priority_ui`'s own screen, and nothing
    else.

    Deliberately thin: this is not `ContainerPriorityDefinition` and
    carries no CPU value, because a discovered container is not yet
    classified as anything. Turning "Docker reports this exists"
    into "the owner has decided this is a priority app / a
    background container / left alone" is `priority_ui/app.py`'s own
    job, reading this alongside the governed YAML — the same split
    `selection_ui/app.py` draws between a scanned catalogue and a
    saved selection.
    """

    name: str
    image: str
    running: bool
    status: str


def resolve_discovered_containers(
    observation: Mapping[str, Any],
) -> tuple[DiscoveredContainer, ...]:
    """
    Shape `aistack.providers.docker.provider.DockerProvider`'s own
    raw observation into what a human choosing priority/throttled
    containers needs.

    **No new provider.** `DockerProvider` already collects `docker
    ps -a --format {{json .}}` — every container's name, image and
    state, observed and unqualified, exactly the shape a provider is
    supposed to have here (its own docstring: "observes ... without
    interpretation"). Deciding what that raw list *means* for this
    feature — one name per container, `State == "running"` read as
    a plain boolean — belongs on this side of the boundary, the same
    split `has_active_playback` draws against `JellyfinProvider`.

    **`-a` (every container, not only running ones) is already
    `DockerProvider`'s own call, kept here rather than filtered
    out.** A container the owner has stopped is still one they may
    want to classify — `docker ps -a` already answers that, and
    `running` on each result is the fact `priority_ui`'s screen
    reads to show which is which, not a reason to hide the stopped
    ones.

    **A container with no name is dropped, never a container with a
    name Docker did not also report a state for.** Every entry
    `docker ps` produces has both; the guard exists only against a
    genuinely empty or malformed record, not as a soft-fail for
    Docker's own well-formed output.

    Sorted by name — a screen listing potentially dozens of
    containers reads better in a stable order than in whatever order
    the Docker daemon happened to answer.
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
    Docker's own `Names` field is a single comma-separated string
    when a container carries more than one name/alias — the first
    is its primary one, and the one every other governed reference
    (`docker inspect`, `docker update`) already addresses it by.
    """

    return str(names).split(",")[0].strip()
