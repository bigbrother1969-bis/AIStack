from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Mapping

# Container identity shared by the Docker collectors (diff, digest,
# packages), read from one `docker inspect` call.
#
# `image_digest` is the container's `.Image`: the image *configuration*
# digest (a local `sha256:...` id). It is not a `RepoDigests` manifest
# digest, which only a registry can compare against; the local id is
# enough to detect an upgrade without a network call.


def stable_subject_from_labels(
    labels: Mapping[str, Any],
    *,
    name: str = "",
    container_id: str = "",
) -> str:
    """Stable subject of a container (`ADR-0011` § Decision 3).

    `project/service` from the Compose labels when both are present, else
    `name`, else `container_id`, else `"unknown"`. Never empty.
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
    """What the Docker monitors need about one running container: its
    stable subject, mount destinations (to exclude user-data volumes) and
    image."""

    name: str
    stable_subject: str
    mount_destinations: tuple[str, ...]
    image_digest: str = ""
    # `Config.Image`, e.g. `wordpress:latest`: what a rollback pins by
    # digest (`ADR-0018`).
    image_name: str = ""


def list_running_container_names() -> list[str]:
    """Names of running containers (`docker ps`); `[]` on any failure."""

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
    """`docker inspect` of all `names` in a single subprocess.

    `[]` on any failure, or when `names` is empty (`docker inspect` with
    no argument is a usage error).
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
    """Identities of the containers `docker inspect` could resolve.

    Not one-to-one with `names`: a container removed since `docker ps` is
    absent from the result.
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
