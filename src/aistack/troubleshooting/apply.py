"""
The one fix the Troubleshooting Assistant knows how to make
(`ADR-0012` § 4; scoped with the owner 2026-09-18).

Declaring a finding's subject a `background` container in the governed
resource-priority definition — the same write the *Priorité CPU* screen
performs, for one container. **Never `priority`**, which needs a
detector and CPU thresholds a single click cannot safely default; and
**never anything derived from the AI's `recommend` text**: this is one
fixed, hand-written change the owner triggers with its own click.
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
    Refused when the subject is already a priority application — that
    classification is the owner's judgement, never overwritten by a
    click; nothing to write when it is already in the background list.
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
