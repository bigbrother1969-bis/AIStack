"""
What the *Priorité CPU* screen shows and saves (`ADR-0012` § 4).

The route in `aistack.web.priority` reads the request and calls these. The
file this screen edits is the one `aistack.cli.resource_priority_monitor`
reads.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass

from aistack.priority.definition import (
    BackgroundPriorityDefinition,
    ContainerPriorityDefinition,
    CpuThresholdDetectorDefinition,
    JellyfinDetectorDefinition,
    PriorityAppDefinition,
    ResourcePriorityDefinition,
)
from aistack.priority.discovery import DiscoveredContainer, resolve_discovered_containers
from aistack.providers.docker import DockerProvider

Discover = Callable[[], tuple[DiscoveredContainer, ...]]


def discover_containers() -> tuple[DiscoveredContainer, ...]:
    """
    What Docker reports right now, or nothing if the daemon is unreachable.

    `DockerProvider` raises when the daemon is down; this call absorbs it so
    the screen still shows the saved classification.
    """

    try:
        return resolve_discovered_containers(DockerProvider().collect())
    except subprocess.CalledProcessError:
        return ()


@dataclass(frozen=True)
class PriorityRow:
    """One container on the screen, beside what the definition says about it."""

    name: str
    image: str
    running: bool | None
    status: str
    classification: str
    priority_app: PriorityAppDefinition | None
    background_container: ContainerPriorityDefinition | None


def priority_rows(
    definition: ResourcePriorityDefinition,
    discovered: tuple[DiscoveredContainer, ...],
) -> list[PriorityRow]:
    """
    Every discovered or declared container joined to the definition, by name.

    A container the definition names but Docker does not report is still
    shown, with `running` set to `None`.
    """

    priority_by_name = {app.container: app for app in definition.priority}
    background_by_name = {c.name: c for c in definition.background.containers}
    discovered_by_name = {c.name: c for c in discovered}

    rows = []

    for name in sorted(set(discovered_by_name) | set(priority_by_name) | set(background_by_name)):
        container = discovered_by_name.get(name)
        priority_app = priority_by_name.get(name)
        background_container = background_by_name.get(name)

        if priority_app is not None:
            classification = "priority"
        elif background_container is not None:
            classification = "throttled"
        else:
            classification = "ignored"

        rows.append(
            PriorityRow(
                name=name,
                image=container.image if container else "",
                running=container.running if container else None,
                status=container.status if container else "",
                classification=classification,
                priority_app=priority_app,
                background_container=background_container,
            )
        )

    return rows


def definition_from_form(
    current: ResourcePriorityDefinition,
    names: set[str],
    form: Mapping[str, str],
) -> ResourcePriorityDefinition:
    """
    Build the definition the screen's form describes, for the containers it
    showed.

    Fields are namespaced by container (`classification__<name>`,
    `normal_cpus__<name>`, ...). A container classified neither priority nor
    throttled is ignored; there is no separate "delete". Values the form does
    not carry (`unlimited_cpus`, `grace_seconds`, the default throttle) are
    kept from `current`.
    """

    priority_entries: list[PriorityAppDefinition] = []
    background_entries: list[ContainerPriorityDefinition] = []

    for name in names:
        classification = form.get(f"classification__{name}", "ignored")

        if classification == "priority":
            priority_entries.append(_priority_app_from_form(form, name))
        elif classification == "throttled":
            background_entries.append(_background_container_from_form(form, name))

    return ResourcePriorityDefinition(
        priority=tuple(sorted(priority_entries, key=lambda app: app.container)),
        background=BackgroundPriorityDefinition(
            default_throttled_cpus=current.background.default_throttled_cpus,
            containers=tuple(sorted(background_entries, key=lambda c: c.name)),
        ),
        unlimited_cpus=current.unlimited_cpus,
        grace_seconds=current.grace_seconds,
    )


def _priority_app_from_form(form: Mapping[str, str], name: str) -> PriorityAppDefinition:
    detector: CpuThresholdDetectorDefinition | JellyfinDetectorDefinition

    if form.get(f"detector_type__{name}", "jellyfin") == "cpu_threshold":
        detector = CpuThresholdDetectorDefinition(
            threshold_percent=_form_float(form, f"cpu_threshold_percent__{name}", default=50.0),
            sustained_seconds=_form_float(form, f"cpu_sustained_seconds__{name}", default=15.0),
        )
    else:
        detector = JellyfinDetectorDefinition(
            url=str(form.get(f"jellyfin_url__{name}", "")),
            api_key_env=str(form.get(f"jellyfin_api_key_env__{name}", "")),
            timeout_seconds=_form_float(form, f"jellyfin_timeout__{name}", default=5.0),
        )

    return PriorityAppDefinition(
        container=name,
        normal_cpus=_form_float(form, f"normal_cpus__{name}", default=0.0),
        boosted_cpus=_form_float(form, f"boosted_cpus__{name}", default=0.0),
        detector=detector,
    )


def _background_container_from_form(
    form: Mapping[str, str], name: str
) -> ContainerPriorityDefinition:
    raw = str(form.get(f"throttled_normal_cpus__{name}", "")).strip()

    # Unlike the other fields, a non-numeric value raises instead of falling
    # back to a default, which would change what the user meant.
    return ContainerPriorityDefinition(name=name, normal_cpus=float(raw) if raw else None)


def _form_float(form: Mapping[str, str], field: str, default: float) -> float:
    raw = str(form.get(field, "")).strip()

    try:
        return float(raw) if raw else default
    except ValueError:
        return default
