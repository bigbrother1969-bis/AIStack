"""
What a runtime says about a container's health, and what it does
not say.

A container without a healthcheck has no health status; it is reported
as undeclared, never as healthy (ADR-0009 § 6).
"""

from __future__ import annotations

from enum import Enum
import re


# `docker ps` puts health inside `Status`: `Up 2 hours (healthy)`,
# `Up 30 seconds (health: starting)`. Only these literals match, since
# other parentheticals such as `Exited (0)` say nothing about health.
DECLARED = re.compile(
    r"\((healthy|unhealthy|health:\s*starting)\)",
    re.I,
)


class ContainerHealth(str, Enum):
    """
    A container's declared health (ADR-0009 § 6).

    `STARTING` is a declared healthcheck that has not returned a verdict
    yet (Docker's `health: starting`, during `--start-period`); it is
    neither undeclared nor unhealthy.
    """

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    UNDECLARED = "undeclared"

    @property
    def is_declared(self) -> bool:
        """Whether the runtime says anything about health at all."""

        return self is not ContainerHealth.UNDECLARED


def health_of(status: str | None) -> ContainerHealth:
    """
    The health a `docker ps` status line declares; `UNDECLARED` when it
    carries no recognised verdict.
    """

    if not status:
        return ContainerHealth.UNDECLARED

    found = DECLARED.search(status)

    if found is None:
        return ContainerHealth.UNDECLARED

    declared = found.group(1).lower()

    if declared.startswith("health:"):
        return ContainerHealth.STARTING

    return ContainerHealth(declared)
