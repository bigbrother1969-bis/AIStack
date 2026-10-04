from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.technical_debt_score import (
    TECHNICAL_DEBT_QUALIFICATION,
    TechnicalDebtScore,
)


def compute_technical_debt_score(
    domains: Sequence[Sequence[RuntimeFinding]], weight: int
) -> TechnicalDebtScore:
    """
    Turn the cockpit's findings, grouped by health domain, into one
    `TechnicalDebtScore`, filtering for `OPS-0004/technical-debt`
    itself rather than trusting the caller to hand in a pre-filtered
    set. Pure: given the same findings and the same weight, always the
    same score.

    `weight` is `OPS-0008`'s own declared "Services" weight, reused
    rather than a new weight declared for this card — the owner's own
    choice, 2026-09-23 ("même poids que le domaine Services actuel").
    Reading and validating that weight is the caller's job
    (`aistack.cli.health_render.technical_debt_score`).

    **Each domain carrying debt costs `weight` once** (`OPS-0008`
    § *Technical debt score*, decided by the owner 2026-10-04):
    `value = max(0, 100 − weight × domains)`, where `domains` counts
    the domains with at least one finding qualified technical debt.
    Until then every finding cost `weight` — on GIGABYTE, 4 restore
    tests and 7 inventory gaps clamped the score to 0 from the seventh
    finding on, so no single correction ever moved it; now it moves
    when a domain is cleared, and the findings themselves stay listed.

    Same bucket thresholds the owner declared for the health score,
    2026-09-23 ("mêmes seuils que le score santé"): `>= 90` excellent,
    `< 75` action requise, otherwise à surveiller — reused from
    `aistack.contracts.health_score` rather than redeclared.

    Findings not qualified `OPS-0004/technical-debt` are silently
    excluded, not an error.
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
