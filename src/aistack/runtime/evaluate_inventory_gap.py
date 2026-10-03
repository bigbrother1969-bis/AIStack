"""
`evaluate_inventory_gap` — the Écarts-d'inventaire-domain analogue of
`evaluate_uncovered_state`/`evaluate_pra_tests`, correlating an
already-confirmed `InventoryGap` into a `RuntimeFinding` citing the
`OPS-0004` qualifications the owner confirmed for 1.6 tranche 3's own
seventh reference case (R9, 2026-09-30).

**A seventh reference case, not an incident.** Like the fourth
(Sauvegarde/PRA), fifth (GPU) and sixth (État persistant) reference
cases, this one names no past failure the owner described after the
fact — it examines a condition against `OPS-0004`'s vocabulary before
any real instance of it was necessarily observed (`GOV-P-001`: the
owner states the knowledge, this module invents nothing beyond it).

**All four qualifications, none excluded** — the third reference case,
after GPU and État persistant, to carry the complete vocabulary.
Examined against `OPS-0004`'s four terms, 2026-09-30, the owner
confirmed all four apply to an inventory gap in either direction:
technical debt, deployment misconfiguration, energy inefficiency, and
sustainability anomaly.

**A separate function, not a branch inside `evaluate`.** Same
reasoning `evaluate_backup`/`evaluate_uncovered_state` already give:
an `InventoryGap` has no second reading to correlate against — the
join `find_inventory_gaps` already performed, between what is
declared and what is actually running, already says whether it
qualifies.
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

# `OPS-0004`'s own vocabulary — see `RuntimeFinding.QUALIFICATIONS` for
# the full closed list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"
ENERGY_INEFFICIENCY = "OPS-0004/energy-inefficiency"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"

# All four qualifications the owner confirmed for this seventh
# reference case, 2026-09-30 — none excluded, the same shape the GPU
# and État-persistant domains' own fifth and sixth reference cases
# took.
INVENTORY_GAP_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    DEPLOYMENT_MISCONFIGURATION,
    ENERGY_INEFFICIENCY,
    SUSTAINABILITY_ANOMALY,
)

# There is no provider behind an `InventoryGap` — it is the direct
# output of `find_inventory_gaps`, a pure join, not a value collected
# from a live system. `CitedReading.provider` still names something,
# the same way `BACKUP_STRATEGY_SOURCE` names the loader itself for a
# `BackupStrategyDeclaration` that was never collected either.
INVENTORY_GAP_SOURCE = "aistack.runtime.inventory_gap.find_inventory_gaps"

# The signature `RuntimeFinding.signature` cites — `OPS-0004` itself,
# the register that authors this correlation, the same role it plays
# for every other domain evaluator in this package.
SIGNATURE = "OPS-0004"


def evaluate_inventory_gap(gaps: Sequence[InventoryGap]) -> tuple[RuntimeFinding, ...]:
    """
    One `RuntimeFinding` per gap `find_inventory_gaps` already found,
    citing all four `OPS-0004` qualifications the owner confirmed for
    this seventh reference case.

    Pure: gaps already found in, findings out — the same discipline
    every other domain evaluator in this package already holds.
    """

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
    # `InventoryGap.__post_init__` already guarantees `kind ==
    # DECLARED_UNDISCOVERED` implies `service is not None` — but that
    # guarantee lives on a different type, so mypy cannot see it from
    # here. Checking both conditions together, rather than asserting
    # past the second one, narrows `service` for this function without
    # a bare `assert` (the same reasoning `evaluate_backup._interpretation`
    # already documents for its own analogous narrowing).
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
