"""
Turn `InventoryGap`s (declared services not running, or running containers
not declared) into `RuntimeFinding`s carrying all four `OPS-0004`
qualifications.
"""

from __future__ import annotations

from aistack.contracts.finding_message import FindingMessage, part

from collections.abc import Sequence

from aistack.contracts.inventory_gap import (
    DECLARED_UNDISCOVERED,
    DISCOVERED_UNDECLARED,
    InventoryGap,
)
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004` vocabulary; `RuntimeFinding.QUALIFICATIONS` holds the full list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"
ENERGY_INEFFICIENCY = "OPS-0004/energy-inefficiency"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"

INVENTORY_GAP_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    DEPLOYMENT_MISCONFIGURATION,
    ENERGY_INEFFICIENCY,
    SUSTAINABILITY_ANOMALY,
)

# A gap comes from a pure join, not from a provider, so the join function
# itself is cited as the source.
INVENTORY_GAP_SOURCE = "aistack.runtime.inventory_gap.find_inventory_gaps"

SIGNATURE = "OPS-0004"


def evaluate_inventory_gap(gaps: Sequence[InventoryGap]) -> tuple[RuntimeFinding, ...]:
    """One `RuntimeFinding` per gap, citing all four `OPS-0004` qualifications."""

    return tuple(
        RuntimeFinding(
            subject=_subject(gap),
            signature=SIGNATURE,
            interpretation=_interpretation(gap),
            remediation=_remediation(gap),
            message=_message(gap),
            confidence="Measured",
            grounding=UNDECLARED,
            evidence=(CitedReading(provider=INVENTORY_GAP_SOURCE, reading=gap),),
            qualifications=INVENTORY_GAP_QUALIFICATIONS,
        )
        for gap in gaps
    )


def _subject(gap: InventoryGap) -> str:
    # DECLARED_UNDISCOVERED implies `service` is set; test both so mypy can
    # narrow the type.
    if gap.kind == DECLARED_UNDISCOVERED and gap.service is not None:
        return gap.service

    return gap.container


def _interpretation(gap: InventoryGap) -> str:
    if gap.kind == DISCOVERED_UNDECLARED:
        where = f"on {gap.host}" if gap.host else "on this host"

        return (
            f"{gap.container} is running {where} but "
            f"service_categorization.yml declares no service for it — "
            f"the condition OPS-0004's seventh reference case names "
            f"(technical debt, deployment misconfiguration, energy "
            f"inefficiency, sustainability anomaly)."
        )

    return (
        f"{gap.service} ({gap.container}) is declared in "
        f"service_categorization.yml but was not found running, "
        f"neither locally nor in the last network discovery — the "
        f"condition OPS-0004's seventh reference case names (technical "
        f"debt, deployment misconfiguration, energy inefficiency, "
        f"sustainability anomaly)."
    )


def _remediation(gap: InventoryGap) -> str:
    if gap.kind == DISCOVERED_UNDECLARED:
        return (
            f"Confirm what {gap.container} is, then either declare it "
            f"in service_categorization.yml or remove it if it should "
            f"not be running — the gap this reference case names, "
            f"never assumed harmless."
        )

    return (
        f"Confirm whether {gap.service} still exists — restore it if "
        f"it should be running, or remove its declaration from "
        f"service_categorization.yml if it no longer applies."
    )


def _message(gap: InventoryGap) -> FindingMessage:
    """The same two sentences as `_interpretation`/`_remediation`, as catalog keys."""

    if gap.kind == DISCOVERED_UNDECLARED:
        interpretation = (
            part(
                "findings.inventory_gap.undeclared_on_host.interpretation",
                container=gap.container,
                host=gap.host,
            )
            if gap.host
            else part(
                "findings.inventory_gap.undeclared_here.interpretation",
                container=gap.container,
            )
        )

        return FindingMessage(
            interpretation=(interpretation,),
            remediation=(
                part("findings.inventory_gap.undeclared.remediation", container=gap.container),
            ),
        )

    return FindingMessage(
        interpretation=(
            part(
                "findings.inventory_gap.missing.interpretation",
                service=gap.service,
                container=gap.container,
            ),
        ),
        remediation=(part("findings.inventory_gap.missing.remediation", service=gap.service),),
    )
