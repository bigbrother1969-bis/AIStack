from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aistack.restart_watch.facts import ContainerFacts

BOOT = datetime(2026, 11, 15, 8, 59, 0, tzinfo=timezone.utc)


def at(seconds: float) -> datetime:
    return BOOT + timedelta(seconds=seconds)


def container(
    name: str,
    *,
    started: float = 10,
    running: bool = True,
    health: str | None = None,
    has_healthcheck: bool | None = None,
    provider: str | None = None,
    depends_on: tuple[str, ...] = (),
) -> ContainerFacts:
    return ContainerFacts(
        name=name,
        container_id=f"id-{name}",
        running=running,
        started_at=at(started),
        health=health,
        has_healthcheck=health is not None if has_healthcheck is None else has_healthcheck,
        network_provider=provider,
        depends_on=depends_on,
    )
