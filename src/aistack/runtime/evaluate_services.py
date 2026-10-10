"""
Turn `ContainerDistress` (restart-looping or unhealthy containers) into
`RuntimeFinding`s.

Always cites three `OPS-0004` qualifications: technical debt, sustainability
anomaly and deployment misconfiguration. Energy inefficiency does not apply
to this domain.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

from collections.abc import Sequence

from aistack.contracts.container_distress import ContainerDistress
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004` vocabulary; `RuntimeFinding.QUALIFICATIONS` holds the full list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

SERVICE_DISTRESS_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    SUSTAINABILITY_ANOMALY,
    DEPLOYMENT_MISCONFIGURATION,
)

# Container state and health are reported by the same Docker provider.
DOCKER_PROVIDER = "aistack.provider.docker"

SIGNATURE = "OPS-0004"


def evaluate_services(
    distress: Sequence[ContainerDistress],
) -> tuple[RuntimeFinding, ...]:
    """One `RuntimeFinding` per container in distress."""

    return tuple(
        RuntimeFinding(
            subject=one.reading.container,
            signature=SIGNATURE,
            interpretation=_interpretation(one),
            message=_message(one),
            remediation=_remediation(one),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(
                CitedReading(provider=DOCKER_PROVIDER, reading=one.reading),
            ),
            qualifications=SERVICE_DISTRESS_QUALIFICATIONS,
        )
        for one in distress
    )


def _interpretation(one: ContainerDistress) -> str:
    reading = one.reading
    reasons = " and ".join(one.reasons)

    return (
        f"{reading.container} is currently {reasons} (state="
        f"{reading.state!r}, health={reading.health.value!r}) — the "
        f"condition OPS-0004's third reference incident names "
        f"(technical debt, sustainability anomaly, deployment "
        f"misconfiguration)."
    )


def _remediation(one: ContainerDistress) -> str:
    return (
        f"Investigate why {one.reading.container} did not restart "
        f"cleanly after its host came back and correct what is "
        f"missing from its boot order or restart policy — the gap the "
        f"power-outage incident named, not a one-time restart of this "
        f"container."
    )


# Which sentence a distressed container gets, by its reasons in order.
_REASON_KEYS = {
    ("restarting",): "findings.services.restarting.interpretation",
    ("unhealthy",): "findings.services.unhealthy.interpretation",
    ("restarting", "unhealthy"): "findings.services.restarting_unhealthy.interpretation",
}


def _message(one: ContainerDistress) -> FindingMessage:
    """The same two sentences as `_interpretation`/`_remediation`, as catalog keys."""

    reading = one.reading

    return FindingMessage(
        interpretation=(
            part(
                _REASON_KEYS[tuple(one.reasons)],
                container=reading.container,
                state=repr(reading.state),
                health=repr(reading.health.value),
            ),
        ),
        remediation=(part("findings.services.remediation", container=reading.container),),
    )
