from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.health_score import BUCKETS
from aistack.contracts.runtime_finding import RuntimeFinding

# The one `OPS-0004` qualification this card scores — see
# `RuntimeFinding.QUALIFICATIONS` for the full closed list. Named here,
# next to the type that enforces it, the same way `container_distress
# .RESTARTING`/`.UNHEALTHY` sit next to `ContainerDistress`.
TECHNICAL_DEBT_QUALIFICATION = "OPS-0004/technical-debt"


@dataclass(frozen=True)
class TechnicalDebtScore:
    """
    One computed "Dette technique" snapshot — `aistack.health
    .technical_debt.compute_technical_debt_score`'s own result, never
    constructed by hand outside a test, the same convention
    `HealthScore` holds for its own computing function.

    **A dedicated card, not a fifth `HealthDomain`** — the owner's own
    choice, 2026-09-23: the four domains `PLAN-J7` already closed stay
    the aggregate `HealthScore`'s only inputs, and `OPS-0004
    /technical-debt` is a *qualification* a finding from any of them
    (Services, Sauvegarde/PRA, GPU, so far) may already carry, not a
    fifth thing to instrument. Folding it into `HealthScore` as well
    would double-count the same findings under two scores; this type
    exists so counting them once, separately, is a real, testable
    claim rather than an implicit side effect of reading `HealthScore`
    twice.

    Unlike `HealthScore`, there is no `measured_domains`/
    `total_domains` pair here — this is not a coverage claim over a
    closed domain set, it is a filtered count over whatever findings
    the cockpit already produced this run. `findings` carries exactly
    the ones counted, so a caller — or a test — can see which ones
    without recomputing the filter itself.
    """

    value: int
    findings: tuple[RuntimeFinding, ...]
    bucket: str

    def __post_init__(self) -> None:
        if not (0 <= self.value <= 100):
            raise ValueError(
                f"a technical-debt score must be within 0-100: {self.value}"
            )

        unqualified = [
            finding.signature
            for finding in self.findings
            if TECHNICAL_DEBT_QUALIFICATION not in finding.qualifications
        ]

        if unqualified:
            raise ValueError(
                f"a technical-debt score carries {len(unqualified)} "
                f"finding(s) not qualified {TECHNICAL_DEBT_QUALIFICATION!r} "
                f"({unqualified}); this card states a filtered count, "
                f"never an unfiltered one"
            )

        if self.bucket not in BUCKETS:
            raise ValueError(
                f"unknown technical-debt-score bucket {self.bucket!r}; "
                f"OPS-0008 declares only {BUCKETS}"
            )
