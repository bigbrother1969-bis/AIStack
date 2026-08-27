"""
What a runtime says about a container's health, and what it does
not say.

The defect this replaces was one expression, in the experimenter
ADR-0009 retired:

    health.get("Status", "healthy")

A container with no healthcheck has no health status, so the
default fired, and the container was displayed as healthy.
Measured on the reference deployment on 2026-08-27: **44 of 61
containers declare no healthcheck**, and every one of them was
shown as sound on no evidence. Seventeen declare one, and all
seventeen were passing.

FDN-0003 Article 12 is the article that forbids it, and its words
are worth quoting because they are narrower than "three states":

> *The absence of validated knowledge is a governed state. The
> absence of knowledge must remain visible. AIStack shall never
> replace missing knowledge with unsupported assumptions.*

What the Article requires is that a missing verdict not be
replaced by a verdict. The names below are ADR-0009 § 6's
rendering of it.
"""

from __future__ import annotations

from enum import Enum
import re


# Docker publishes health inside `Status`, not as a field of its
# own: `Up 2 hours (healthy)`, `Up 30 seconds (health: starting)`.
# `docker ps` carries no other trace of it, and `docker inspect`
# is a second call this provider does not make.
#
# The three literals are matched rather than any parenthetical,
# because `Status` carries others that mean nothing about health —
# `Exited (0) 2 days ago` being the common one.
DECLARED = re.compile(
    r"\((healthy|unhealthy|health:\s*starting)\)",
    re.I,
)


class ContainerHealth(str, Enum):
    """
    Four states, and the fourth was an act of its own.

    ADR-0009 § 6 named three — healthy, unhealthy, undeclared —
    and a fourth condition has no cell among them: a container
    whose healthcheck is declared and has not yet returned a
    verdict. Docker calls it `health: starting`.

    Folding it into `UNDECLARED` would say no healthcheck exists
    where one does. Folding it into `UNHEALTHY` would state a
    verdict nobody reached — the original defect, in the other
    direction. Either is what Article 12 forbids.

    **Decided 2026-08-27 by the owner**, on a measurement that
    found none of it: at that instant the deployment held 44
    containers declaring nothing and 17 passing, and zero
    starting. That is an instant and not an absence — the state is
    transitory by construction, and each of the seventeen passes
    through it on every restart, for the length of its
    `--start-period`. Without this member the only moment a sound
    container is mislabelled is the moment it is watched most
    closely: just after someone restarted it.

    Widening a vocabulary is a separate act — ADR-0009 says so of
    itself, in its own § Status, about `OPS-` and `Operations`.
    This is that act, and it is recorded in ADR-0009 v1.8 rather
    than performed quietly here.
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
    The health a `docker ps` status line declares.

    `UNDECLARED` is returned for a status carrying no health
    verdict this function recognises, and that is the honest
    claim rather than a cautious one: it says *nothing here
    states a verdict*, which is true whether the container has no
    healthcheck or Docker has changed its wording. What it never
    does is name a verdict nobody gave.
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
