from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH
from aistack.contracts.runtime_finding import RuntimeFinding
from aistack.contracts.technical_debt_score import (
    TECHNICAL_DEBT_QUALIFICATION,
    TechnicalDebtScore,
)


def compute_technical_debt_score(
    findings: Sequence[RuntimeFinding], weight: int
) -> TechnicalDebtScore:
    """
    Turn an already-built set of `RuntimeFinding`s into one
    `TechnicalDebtScore`, filtering for `OPS-0004/technical-debt`
    itself rather than trusting the caller to hand in a pre-filtered
    set — the same "this function derives it, never the reverse"
    discipline `compute_health_score` already holds one level up.
    Pure: given the same findings and the same weight, always the
    same score.

    `weight` is `OPS-0008`'s own declared "Services" weight, reused
    rather than a new weight declared for this card — the owner's own
    choice, 2026-09-23 ("même poids que le domaine Services actuel"):
    the reference incident this card was seeded on (containers stuck
    after a power outage) is the same one `evaluate_services` already
    scores 15 points against under Services, so counting it again
    under a different number here would be two prices for the one
    incident. Reading and validating that weight is this function's
    caller's job (`aistack.cli.health_render.technical_debt_score`
    mirrors `compute_health_score`'s own "no weight for domain"
    defect for the one domain this reuses); this function only
    applies whatever `weight` it is handed.

    `value = max(0, 100 − weight × count)`, `compute_health_score`'s
    own formula, cumulative the same way: three findings cost three
    times `weight`, not a flat penalty per run. Same bucket thresholds
    the owner declared for the health score, 2026-09-23 ("mêmes seuils
    que le score santé"): `>= 90` excellent, `< 75` action requise,
    otherwise à surveiller — reused from `aistack.contracts
    .health_score` rather than redeclared, the same governed-value
    reuse the weight itself gets.

    Findings not qualified `OPS-0004/technical-debt` are silently
    excluded, not an error — this mirrors `find_container_distress`
    excluding a reading that matches no reason, not
    `TechnicalDebtScore.__post_init__`'s own check, which instead
    guards this function's own output against ever constructing the
    opposite mistake.
    """

    debt_findings = tuple(
        finding
        for finding in findings
        if TECHNICAL_DEBT_QUALIFICATION in finding.qualifications
    )

    value = max(0, 100 - len(debt_findings) * weight)

    if value >= 90:
        bucket = EXCELLENT
    elif value < 75:
        bucket = ACTION_REQUIRED
    else:
        bucket = TO_WATCH

    return TechnicalDebtScore(value=value, findings=debt_findings, bucket=bucket)
