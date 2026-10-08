"""
What the dock could update now (`ADR-0019` § 1): for each container of
a governed service, the image it runs, the registry digest it was
pulled as, and the digest the registry publishes today for the same
tag. Different digests: an update is available. Read-only — Docker and
the registry are asked, nothing is pulled.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from aistack.dock.declaration import GovernedService
from aistack.dock.registry import parse_reference, published_digest
from aistack.sandbox.run import Runner

WATCHTOWER_LABEL = "com.centurylinklabs.watchtower.enable"
_COMPOSE = (
    "com.docker.compose.project",
    "com.docker.compose.service",
    "com.docker.compose.project.working_dir",
)


@dataclass(frozen=True)
class Candidate:
    service: str
    container: str
    image: str = ""
    image_id: str = ""
    running_digest: str = ""
    published_digest: str = ""
    watchtower: bool = False
    compose_project: str = ""
    compose_service: str = ""
    compose_dir: str = ""
    problem: str = ""

    @property
    def update_available(self) -> bool:
        return bool(
            not self.problem and self.running_digest and self.published_digest
            and self.running_digest != self.published_digest
        )


def _running_digest(runner: Runner, image_id: str, image: str) -> str:
    """The registry digest this local image was pulled as, for its own
    repository (an image can carry several)."""

    shown = runner(["image", "inspect", "--format", "{{json .RepoDigests}}", image_id], 30)
    try:
        digests = json.loads(shown.stdout.strip() or "[]") if shown.returncode == 0 else []
    except json.JSONDecodeError:
        digests = []
    repository = parse_reference(image).short_repository
    for entry in digests:
        name, _, digest = str(entry).partition("@")
        if name == repository:
            return digest
    return ""


def inspect_service(
    service: GovernedService,
    runner: Runner,
    publisher: Callable[[str], str] = published_digest,
) -> list[Candidate]:
    found = []
    for container in service.containers:
        shown = runner(["inspect", "--format", "{{json .}}", container], 30)
        if shown.returncode != 0:
            found.append(Candidate(service.name, container, problem="no such container on this host"))
            continue
        try:
            entry = json.loads(shown.stdout)
        except json.JSONDecodeError:
            found.append(Candidate(service.name, container, problem="docker inspect gave no JSON"))
            continue
        config = entry.get("Config") or {}
        labels = config.get("Labels") or {}
        image = str(config.get("Image") or "")
        image_id = str(entry.get("Image") or "")
        problem = ""
        running = _running_digest(runner, image_id, image) if image else ""
        published = ""
        if "@" in image:
            problem = "pinned by digest: nothing to propose until the pin is removed"
        elif not running:
            problem = "the running image has no registry digest (built locally?)"
        else:
            try:
                published = publisher(image)
            except LookupError as error:
                problem = str(error)
            except OSError as error:
                problem = f"registry not reachable: {error}"
        found.append(Candidate(
            service=service.name, container=container, image=image, image_id=image_id,
            running_digest=running, published_digest=published,
            watchtower=str(labels.get(WATCHTOWER_LABEL, "")).lower() == "true",
            compose_project=str(labels.get(_COMPOSE[0], "")),
            compose_service=str(labels.get(_COMPOSE[1], "")),
            compose_dir=str(labels.get(_COMPOSE[2], "")),
            problem=problem,
        ))
    return found


def inspect_all(
    services: Sequence[GovernedService],
    runner: Runner,
    publisher: Callable[[str], str] = published_digest,
) -> list[Candidate]:
    return [candidate for service in services for candidate in inspect_service(service, runner, publisher)]
