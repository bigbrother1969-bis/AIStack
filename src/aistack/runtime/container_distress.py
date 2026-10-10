from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.container_distress import (
    RESTARTING,
    UNHEALTHY,
    ContainerDistress,
)
from aistack.contracts.container_health import ContainerHealth
from aistack.contracts.container_state_reading import ContainerStateReading


def find_container_distress(
    readings: Sequence[ContainerStateReading],
) -> tuple[ContainerDistress, ...]:
    """
    Return the containers that are restart-looping or unhealthy at the time
    of the reading (no counting over time).

    `ContainerHealth.STARTING` and `.UNDECLARED` never qualify: `STARTING` is
    transitory on every restart with a healthcheck (ADR-0009 § 6), and
    `UNDECLARED` states no verdict.
    """

    distress: list[ContainerDistress] = []

    for reading in readings:
        reasons: list[str] = []

        if reading.state == RESTARTING:
            reasons.append(RESTARTING)

        if reading.health == ContainerHealth.UNHEALTHY:
            reasons.append(UNHEALTHY)

        if reasons:
            distress.append(
                ContainerDistress(reading=reading, reasons=tuple(reasons))
            )

    return tuple(distress)
