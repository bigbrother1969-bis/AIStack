from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping

# 1.5's second collector (`docker diff` periodic), cadrage 2026-09-28 —
# the owner's own decision: factor the identity rule out of
# `aistack.providers.docker.events` (built for 1.5's first collector,
# cabled to a Docker *event*'s own `Actor.Attributes` shape) into a
# shared module the same day, before `docker diff`, dérive du digest,
# and inventaire des paquets would each otherwise have needed their own
# copy of the same rule against a different input shape (`docker
# inspect`'s own `Config.Labels`, a plain dict, not an event's actor).
#
# `image_digest` added 2026-09-28 alongside 1.5's third collector
# (`aistack.providers.docker.digest`, cadrage the same day): the
# owner's own decision was to extend `ContainerIdentity` here rather
# than have that collector run its own second `docker inspect` — this
# module already reads every field `docker inspect` reports for a
# container in one call, and a container's own `.Image` (its current
# image's own *configuration* digest, a `sha256:...` id) is already
# right there in the same JSON entry `mount_destinations` is built
# from. Verified 2026-09-28 (GitHub issue search, `pmdroid/barkvisor`
# #642, and Moby's own v27.5.1 behaviour it cites): this is a
# different digest from an image's own `RepoDigests` (a *manifest*
# digest, comparable only to what a registry itself reports, and not
# reliably present on a container inspect at all) — the two are not
# interchangeable, so this module states plainly which one it captures
# rather than calling it just "the digest". Cadrage decision 4 for
# `docker diff` already fixed the scope this needs: a purely local
# comparison against the last digest observed for the same
# `aistack:stableSubject`, never a registry call — `.Image` is exactly
# the field that comparison needs, and the only one two successive
# `docker inspect` calls on this project's own hosts can compare
# without a network fetch on either side.


def stable_subject_from_labels(
    labels: Mapping[str, Any],
    *,
    name: str = "",
    container_id: str = "",
) -> str:
    """
    `ADR-0011` § *Decision* 3's identity rule, generalised off any
    source of Compose labels — `aistack.providers.docker.events
    .stable_subject_of`'s own logic, unchanged, just no longer cabled
    to a Docker event's own `Actor.Attributes` shape: the Compose
    project and service name when both labels are present
    (`com.docker.compose.project`/`com.docker.compose.service`, the
    same two labels `NetworkDockerDiscoveryProvider` already reads for
    the same reason), falling back to `name`, then `container_id`,
    never empty.
    """

    project = labels.get("com.docker.compose.project")
    service = labels.get("com.docker.compose.service")
    if project and service:
        return f"{project}/{service}"

    if name:
        return name

    if container_id:
        return container_id

    return "unknown"


@dataclass(frozen=True)
class ContainerIdentity:
    """
    What every 1.5 monitor that enumerates running containers needs
    to know about one of them — its own stable identity (§ 3) and its
    declared mount destinations, the one real, per-container fact `R2`
    (excluding user-data volumes) can be checked against, rather than
    guessed at from a path's own name.
    """

    name: str
    stable_subject: str
    mount_destinations: tuple[str, ...]
    image_digest: str = ""
    # The image name the container was started from (`Config.Image`,
    # e.g. `wordpress:latest`) — what a rollback pins, by digest
    # (`ADR-0018`, 1.9).
    image_name: str = ""


def list_running_container_names() -> list[str]:
    """
    Every container `docker ps` reports as currently running, by name
    — `[]` on any failure (no daemon, no such command, malformed
    output), the same convention `aistack.providers.docker.events
    .collect_docker_events` already holds: what could not be observed
    is reported as nothing observed, never raised.
    """

    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def inspect_containers(names: list[str]) -> list[dict[str, Any]]:
    """
    `docker inspect <name...>`, every container in one call rather
    than one subprocess per name — `docker inspect` already accepts
    more than one reference and returns one JSON array, so a cycle
    polling a dozen containers pays for one process, not a dozen.

    `[]` on any failure, or when `names` is empty (`docker inspect`
    with no argument is a usage error, not "nothing to inspect").
    """

    if not names:
        return []

    try:
        result = subprocess.run(
            ["docker", "inspect", *names],
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

    return parsed if isinstance(parsed, list) else []


def identities_of(names: list[str]) -> list[ContainerIdentity]:
    """
    `inspect_containers(names)`, normalised into what every caller
    actually needs — never one-to-one with `names` itself: a
    container removed between `docker ps` and this call is simply
    absent from `docker inspect`'s own answer (Docker itself reports
    an error only when the *whole* command fails, handled by
    `inspect_containers` returning `[]`), so this returns exactly the
    identities Docker could actually still resolve, matched by each
    entry's own `Name` field — not `names` echoed back uninspected.
    """

    identities: list[ContainerIdentity] = []

    for entry in inspect_containers(names):
        if not isinstance(entry, dict):
            continue

        raw_name = entry.get("Name")
        name = str(raw_name).lstrip("/") if raw_name else ""
        if not name:
            continue

        config = entry.get("Config")
        labels = config.get("Labels") if isinstance(config, dict) else None
        labels = labels if isinstance(labels, dict) else {}

        container_id = entry.get("Id")

        mounts = entry.get("Mounts")
        destinations = tuple(
            str(mount["Destination"])
            for mount in mounts
            if isinstance(mount, dict) and mount.get("Destination")
        ) if isinstance(mounts, list) else ()

        raw_image = entry.get("Image")
        image_digest = str(raw_image) if raw_image else ""
        configured_image = config.get("Image") if isinstance(config, dict) else None

        identities.append(
            ContainerIdentity(
                name=name,
                stable_subject=stable_subject_from_labels(
                    labels, name=name, container_id=str(container_id or "")
                ),
                mount_destinations=destinations,
                image_digest=image_digest,
                image_name=str(configured_image) if configured_image else "",
            )
        )

    return identities
