"""
`evaluate_services` — the Services-domain analogue of `evaluate_storage`,
correlating an already-confirmed `ContainerDistress` into a
`RuntimeFinding` citing the three `OPS-0004` qualifications the owner
confirmed for the third reference incident: a sudden power outage
after which containers were observed restart-looping or stuck
unhealthy, visible via the Raspberry's own Homepage page
(`OPS-0004` § *Third reference incident*, `PLAN-J7`,
`claude/PLAN-J7-HEALTH-COCKPIT-2026-09-11.md`).

**A separate function, not a branch inside `evaluate`.** Same reasoning
`evaluate_storage`'s own docstring gives: `evaluate` pairs two
independently-collected readings (CPU, temperature) into a correlated
finding; a `ContainerDistress` has no second reading to correlate
against — a container's own state and health, read once, already say
whether it qualifies (`find_container_distress`, against `OPS-0004`).

**Qualifications are fixed, not derived per finding.** Unlike
`evaluate_storage`, which always cites the single qualification the
second reference incident named, this one always cites three —
technical debt, sustainability anomaly, deployment misconfiguration —
because that is what the owner found the *incident* to carry, examined
once against the full vocabulary (`OPS-0004` § *Third reference
incident*), not something re-derived per container. Energy
inefficiency was explicitly excluded by the owner for this case and is
never cited here.
"""

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.container_distress import ContainerDistress
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004`'s own vocabulary — see `RuntimeFinding.QUALIFICATIONS` for
# the full closed list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"

# The three qualifications the owner confirmed for the third reference
# incident — energy inefficiency was examined and explicitly excluded.
SERVICE_DISTRESS_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    SUSTAINABILITY_ANOMALY,
    DEPLOYMENT_MISCONFIGURATION,
)

# The `provider_id` `DockerProvider.provider_id` declares — the same
# provider that already collects logs, CPU and commands for this
# subject; a container's state and health are one more thing Docker
# itself reports, not a second provider.
DOCKER_PROVIDER = "aistack.provider.docker"

# The signature `RuntimeFinding.signature` cites — `OPS-0004` itself,
# the register that authors this correlation, the same role it plays
# for `evaluate_storage`.
SIGNATURE = "OPS-0004"


def evaluate_services(
    distress: Sequence[ContainerDistress],
) -> tuple[RuntimeFinding, ...]:
    """
    One `RuntimeFinding` per container `find_container_distress`
    already found in distress, citing the three qualifications the
    owner confirmed for `OPS-0004`'s third reference incident.

    Pure: distress already found in, findings out — the same
    discipline `evaluate_storage` holds.
    """

    return tuple(
        RuntimeFinding(
            subject=one.reading.container,
            signature=SIGNATURE,
            interpretation=_interpretation(one),
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
