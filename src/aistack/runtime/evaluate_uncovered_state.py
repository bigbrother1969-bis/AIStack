"""
Turn `UncoveredStateGap`s (stateful services with no backup engine, `OPS-0010`)
into `RuntimeFinding`s carrying all four `OPS-0004` qualifications.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

from collections.abc import Sequence

from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.uncovered_state_gap import UncoveredStateGap
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004` vocabulary; `RuntimeFinding.QUALIFICATIONS` holds the full list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"
ENERGY_INEFFICIENCY = "OPS-0004/energy-inefficiency"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"

UNCOVERED_STATE_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    DEPLOYMENT_MISCONFIGURATION,
    ENERGY_INEFFICIENCY,
    SUSTAINABILITY_ANOMALY,
)

# A declaration is loaded from YAML, not collected by a provider, so the
# loader itself is cited as the source.
BACKUP_STRATEGY_SOURCE = "aistack.backup_strategy.yaml.load_backup_strategy_yaml"

SIGNATURE = "OPS-0004"


def evaluate_uncovered_state(
    gaps: Sequence[UncoveredStateGap],
) -> tuple[RuntimeFinding, ...]:
    """One `RuntimeFinding` per gap, citing all four `OPS-0004` qualifications."""

    return tuple(
        RuntimeFinding(
            subject=gap.declaration.service,
            signature=SIGNATURE,
            interpretation=_interpretation(gap),
            remediation=_remediation(gap),
            message=_message(gap),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(
                CitedReading(
                    provider=BACKUP_STRATEGY_SOURCE, reading=gap.declaration
                ),
            ),
            qualifications=UNCOVERED_STATE_QUALIFICATIONS,
        )
        for gap in gaps
    )


def _interpretation(gap: UncoveredStateGap) -> str:
    service = gap.declaration.service

    return (
        f"{service} holds persistent state with no known backup engine "
        f"covering it — the condition OPS-0010's état-persistant constat "
        f"names (technical debt, deployment misconfiguration, energy "
        f"inefficiency, sustainability anomaly)."
    )


def _remediation(gap: UncoveredStateGap) -> str:
    service = gap.declaration.service

    return (
        f"Confirm or put in place a real backup mechanism for {service}'s "
        f"persistent state, then record its engine in OPS-0010's own "
        f"declared file — the gap this reference case names, not a "
        f"one-time manual backup."
    )


def _message(gap: UncoveredStateGap) -> FindingMessage:
    """The same two sentences as `_interpretation`/`_remediation`, as catalog keys."""

    service = gap.declaration.service

    return FindingMessage(
        interpretation=(part("findings.uncovered_state.interpretation", service=service),),
        remediation=(part("findings.uncovered_state.remediation", service=service),),
    )
