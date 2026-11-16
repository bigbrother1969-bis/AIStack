from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH, HealthScoreWeights
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.technical_debt_score import (
    TECHNICAL_DEBT_QUALIFICATION,
    TechnicalDebtScore,
)
from aistack.health.cockpit import HealthCockpit


def compute_technical_debt_score(
    domains: Sequence[Sequence[RuntimeFinding]], weight: int
) -> TechnicalDebtScore:
    """
    Compute the `TechnicalDebtScore` from the cockpit's findings, grouped by
    domain, keeping only findings qualified `OPS-0004/technical-debt`.

    Each domain carrying debt costs `weight` once:
    `value = max(0, 100 - weight × domains)`, so clearing a domain moves the
    score even when it holds many findings. `weight` is the `OPS-0008`
    "Services" weight, read by the caller. Buckets use the health score
    thresholds. Pure.
    """

    per_domain = [
        tuple(finding for finding in findings if TECHNICAL_DEBT_QUALIFICATION in finding.qualifications)
        for findings in domains
    ]
    debt_findings = tuple(finding for findings in per_domain for finding in findings)
    touched = sum(1 for findings in per_domain if findings)

    value = max(0, 100 - touched * weight)

    if value >= 90:
        bucket = EXCELLENT
    elif value < 75:
        bucket = ACTION_REQUIRED
    else:
        bucket = TO_WATCH

    return TechnicalDebtScore(value=value, findings=debt_findings, bucket=bucket)


def technical_debt_score(
    cockpit: HealthCockpit,
    weights: HealthScoreWeights | None,
) -> tuple[TechnicalDebtScore | None, str]:
    """
    Score the technical-debt findings of every domain in `cockpit`.

    Uses the Services weight of OPS-0008. Returns `(None, note)` without
    weights, `(score, "")` otherwise; raises when the weights lack a
    Services entry.
    """

    if weights is None:
        return None, (
            "no health-score weight definition available; technical-debt "
            "score is not computed"
        )

    points = weights.for_domain("Services")

    if points is None:
        raise ValueError(
            "OPS-0008 declares no weight for domain 'Services'; the "
            "technical-debt score reuses it and cannot be computed "
            "without it"
        )

    groups = tuple(tuple(domain.findings) for domain in cockpit.domains)

    return compute_technical_debt_score(groups, points), ""
