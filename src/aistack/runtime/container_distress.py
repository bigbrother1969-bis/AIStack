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
    Which containers `OPS-0004`'s third reference incident names as a
    problem: restart-looping, or declared unhealthy — read at one
    instant, never counted over time (the owner's chosen v1 scope,
    2026-09-11).

    Mirrors `find_storage_shortage`: given readings already collected,
    decides which are actually in distress — it never proposes the
    rule itself, and a reading matching neither condition is silently
    not flagged, not treated as sound.

    `ContainerHealth.STARTING` and `.UNDECLARED` never qualify.
    `STARTING` is transitory by construction (ADR-0009 § 6 — every
    container with a healthcheck passes through it on every restart,
    for the length of its `--start-period`); `UNDECLARED` states no
    verdict at all. Citing either as distress would be exactly what
    `FDN-0003` Article 12 forbids: a verdict nobody reached.

    Pure: readings already collected in, distress out — the same
    discipline `find_storage_shortage` already holds.
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
