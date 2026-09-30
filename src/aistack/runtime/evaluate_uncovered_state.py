"""
`evaluate_uncovered_state` — the État-persistant-domain analogue of
`evaluate_pra_tests`/`evaluate_backup`, correlating an
already-confirmed `UncoveredStateGap` into a `RuntimeFinding` citing
the `OPS-0004` qualifications the owner confirmed for 1.6 tranche 2's
own sixth reference case (R9, 2026-09-30).

**A sixth reference case, not an incident.** Like the fourth
(Sauvegarde/PRA) and fifth (GPU) reference cases, this one names no
past failure the owner described after the fact — it examines a
condition against `OPS-0004`'s vocabulary before any real instance of
it was necessarily observed (`GOV-P-001`: the owner states the
knowledge, this module invents nothing beyond it).

**All four qualifications, none excluded** — the second reference
case, after GPU, to carry the complete vocabulary. Examined against
`OPS-0004`'s four terms, 2026-09-30, the owner confirmed all four
apply to a stateful service with no known backup engine: technical
debt, deployment misconfiguration, energy inefficiency, and
sustainability anomaly.

**A separate function, not a branch inside `evaluate`.** Same
reasoning `evaluate_backup`/`evaluate_pra_tests` already give: an
`UncoveredStateGap` has no second reading to correlate against — a
declared service's own state/engine declaration, read once, already
says whether it qualifies (`find_uncovered_state`, against
`OPS-0010`).
"""

from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.uncovered_state_gap import UncoveredStateGap
from aistack.contracts.undeclared import UNDECLARED

# `OPS-0004`'s own vocabulary — see `RuntimeFinding.QUALIFICATIONS` for
# the full closed list.
TECHNICAL_DEBT = "OPS-0004/technical-debt"
DEPLOYMENT_MISCONFIGURATION = "OPS-0004/deployment-misconfiguration"
ENERGY_INEFFICIENCY = "OPS-0004/energy-inefficiency"
SUSTAINABILITY_ANOMALY = "OPS-0004/sustainability-anomaly"

# All four qualifications the owner confirmed for this sixth reference
# case, 2026-09-30 — none excluded, the same shape the GPU domain's
# own fifth reference case took.
UNCOVERED_STATE_QUALIFICATIONS = (
    TECHNICAL_DEBT,
    DEPLOYMENT_MISCONFIGURATION,
    ENERGY_INEFFICIENCY,
    SUSTAINABILITY_ANOMALY,
)

# There is no provider behind a `BackupStrategyDeclaration` — it is
# loaded directly from `OPS-0010`'s declared YAML
# (`aistack.backup_strategy.yaml.load_backup_strategy_yaml`), not
# collected from a live system. `CitedReading.provider` still names
# something, the same way `PRA_TESTS_SOURCE` names the loader itself
# for `PraTestReading`.
BACKUP_STRATEGY_SOURCE = "aistack.backup_strategy.yaml.load_backup_strategy_yaml"

# The signature `RuntimeFinding.signature` cites — `OPS-0004` itself,
# the register that authors this correlation, the same role it plays
# for `evaluate_backup`/`evaluate_pra_tests`.
SIGNATURE = "OPS-0004"


def evaluate_uncovered_state(
    gaps: Sequence[UncoveredStateGap],
) -> tuple[RuntimeFinding, ...]:
    """
    One `RuntimeFinding` per declared service `find_uncovered_state`
    already found failing, citing all four `OPS-0004` qualifications
    the owner confirmed for this sixth reference case.

    Pure: gaps already found in, findings out — the same discipline
    `evaluate_backup`/`evaluate_pra_tests` already hold.
    """

    return tuple(
        RuntimeFinding(
            subject=gap.declaration.service,
            signature=SIGNATURE,
            interpretation=_interpretation(gap),
            remediation=_remediation(gap),
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
