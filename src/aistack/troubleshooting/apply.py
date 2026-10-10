"""
The one fix the Troubleshooting Assistant can apply (`ADR-0012` § 4):
declaring a finding's subject a `background` container in the
resource-priority definition, as the *Priorité CPU* screen does.

Never `priority`, which needs a detector and thresholds a click cannot
safely default, and never anything derived from the AI's text.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from aistack.priority.definition import ContainerPriorityDefinition, ResourcePriorityDefinition


class BackgroundChange(StrEnum):
    ADDED = "added"
    ALREADY_BACKGROUND = "already_background"
    REFUSED_PRIORITY = "refused_priority"


@dataclass(frozen=True)
class BackgroundDecision:
    """What classing `subject` as background does: the change, and the definition to save if any."""

    change: BackgroundChange
    updated: ResourcePriorityDefinition | None


def class_as_background(
    definition: ResourcePriorityDefinition, subject: str
) -> BackgroundDecision:
    """
    Add `subject` to the background containers. Refused when it is a
    priority app (a user decision a click never overwrites); nothing to
    write when it is already in the background list.
    """

    if any(app.container == subject for app in definition.priority):
        return BackgroundDecision(BackgroundChange.REFUSED_PRIORITY, None)

    if any(container.name == subject for container in definition.background.containers):
        return BackgroundDecision(BackgroundChange.ALREADY_BACKGROUND, None)

    containers = tuple(
        sorted(
            (*definition.background.containers, ContainerPriorityDefinition(name=subject)),
            key=lambda container: container.name,
        )
    )

    return BackgroundDecision(
        BackgroundChange.ADDED,
        replace(definition, background=replace(definition.background, containers=containers)),
    )
