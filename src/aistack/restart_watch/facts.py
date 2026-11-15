from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

# Docker prints nanoseconds; Python reads microseconds.
_FRACTION = re.compile(r"(\.\d{6})\d+")

COMPOSE_PROJECT = "com.docker.compose.project"
COMPOSE_SERVICE = "com.docker.compose.service"
COMPOSE_DEPENDS_ON = "com.docker.compose.depends_on"
NETWORK_PREFIX = "container:"

Run = Callable[[Sequence[str]], "subprocess.CompletedProcess[str]"]


@dataclass(frozen=True)
class ContainerFacts:
    """
    What Docker says about one container, reduced to what the watch judges.

    `network_provider` is the name of the container whose network this one
    shares (`network_mode: container:<id>`), resolved by `read_facts`;
    `depends_on` holds the *container* names of its Compose dependencies.
    `health` is `None` when the image declares no healthcheck.
    """

    name: str
    container_id: str
    running: bool
    started_at: datetime | None
    health: str | None
    has_healthcheck: bool
    network_provider: str | None = None
    depends_on: tuple[str, ...] = ()


def run_docker(arguments: Sequence[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        ["docker", *arguments], capture_output=True, text=True, timeout=60, check=False
    )


def parse_time(value: str | None) -> datetime | None:
    """Docker's `StartedAt`; `None` for the zero date of a container never started."""

    if not value or value.startswith("0001-"):
        return None

    try:
        return datetime.fromisoformat(
            _FRACTION.sub(r"\1", value).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except ValueError:
        return None


def read_facts(run: Run = run_docker) -> tuple[ContainerFacts, ...]:
    """Every container's facts, from one `docker ps` and one `docker inspect`."""

    listing = run(["ps", "-aq", "--no-trunc"])

    if listing.returncode != 0:
        raise RuntimeError(listing.stderr.strip() or "docker ps failed")

    identifiers = listing.stdout.split()

    if not identifiers:
        return ()

    inspected = run(["inspect", *identifiers])

    if inspected.returncode != 0:
        raise RuntimeError(inspected.stderr.strip() or "docker inspect failed")

    return parse_inspect(json.loads(inspected.stdout))


def parse_inspect(documents: Sequence[dict[str, Any]]) -> tuple[ContainerFacts, ...]:
    """Pure: `docker inspect` output to facts, with providers and dependencies resolved to names."""

    names = {doc["Id"]: str(doc["Name"]).lstrip("/") for doc in documents}
    by_service = {
        (labels.get(COMPOSE_PROJECT), labels.get(COMPOSE_SERVICE)): names[doc["Id"]]
        for doc in documents
        if (labels := (doc.get("Config") or {}).get("Labels") or {})
        and labels.get(COMPOSE_SERVICE)
    }
    found: list[ContainerFacts] = []

    for doc in documents:
        config = doc.get("Config") or {}
        state = doc.get("State") or {}
        labels = config.get("Labels") or {}
        mode = str((doc.get("HostConfig") or {}).get("NetworkMode") or "")
        provider: str | None = None

        if mode.startswith(NETWORK_PREFIX):
            target = mode[len(NETWORK_PREFIX):]
            provider = names.get(target) or next(
                (name for ident, name in names.items() if ident.startswith(target)),
                target if target in names.values() else None,
            )

        depends = tuple(
            sorted(
                {
                    by_service[(labels.get(COMPOSE_PROJECT), service)]
                    for service in _dependency_services(labels.get(COMPOSE_DEPENDS_ON))
                    if (labels.get(COMPOSE_PROJECT), service) in by_service
                }
            )
        )
        health = (state.get("Health") or {}).get("Status")
        test = (config.get("Healthcheck") or {}).get("Test") or []

        found.append(
            ContainerFacts(
                name=names[doc["Id"]],
                container_id=doc["Id"],
                running=bool(state.get("Running")) and not state.get("Restarting"),
                started_at=parse_time(state.get("StartedAt")),
                health=str(health) if health else None,
                has_healthcheck=bool(test) and list(test) != ["NONE"],
                network_provider=provider,
                depends_on=depends,
            )
        )

    return tuple(sorted(found, key=lambda facts: facts.name))


def _dependency_services(label: str | None) -> list[str]:
    """`gluetun:service_started:false,db:service_healthy:true` to the service names."""

    if not label:
        return []

    return [part.split(":", 1)[0] for part in label.split(",") if part.strip()]
