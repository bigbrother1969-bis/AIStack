from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.health_score import BUCKETS
from aistack.contracts.runtime_finding import RuntimeFinding

# The OPS-0004 qualification this card scores (see `QUALIFICATIONS`).
TECHNICAL_DEBT_QUALIFICATION = "OPS-0004/technical-debt"


@dataclass(frozen=True)
class TechnicalDebtScore:
    """
    One computed technical-debt score, produced by
    `aistack.health.technical_debt.compute_technical_debt_score`.

    A separate card, not a health domain: technical debt is a
    qualification that findings of any domain may carry, so folding it
    into `HealthScore` would count them twice. `findings` holds exactly
    the findings counted; each must carry the qualification.
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
