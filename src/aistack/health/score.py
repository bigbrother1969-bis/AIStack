from __future__ import annotations

from aistack.contracts.health_score import (
    ACTION_REQUIRED,
    EXCELLENT,
    TO_WATCH,
    HealthScore,
    HealthScoreWeights,
)
from aistack.health.cockpit import HealthCockpit


def compute_health_score(
    cockpit: HealthCockpit, weights: HealthScoreWeights
) -> HealthScore:
    """
    Turn an already-built `HealthCockpit` into one `HealthScore`,
    reading `OPS-0008`'s declared weights rather than inventing any —
    the same "the score remains a display derived from governed
    findings, never the reverse" discipline `PLAN-J7` § 5 states and
    every domain's own `evaluate_*` function already holds one level
    down. Pure — the same `render_html`/`evaluate_*` convention: given
    the same cockpit and the same weights, always the same score.

    `value = max(0, 100 − Σ penalty)`, the formula the owner declared
    2026-09-11 (`OPS-0008` § *Formula*): a domain not instrumented
    contributes no penalty and is excluded from the count entirely —
    the same `FDN-0003` Article 12 absence `HealthDomain` itself
    already enforces, never smoothed into either a penalty or a clean
    pass here. Findings within one instrumented domain are cumulative:
    a domain carrying three findings costs three times its own weight,
    the owner's own explicit choice over a flat per-domain penalty.

    Raises if a cockpit names a domain `weights` has no entry for —
    `PLAN-J7`'s domain vocabulary is closed at four, and `OPS-0008` is
    expected to cover it completely; a domain missing its own weight
    is a configuration defect, not a governed absence, so this does
    not degrade quietly the way a missing threshold file does.
    """

    measured = tuple(domain for domain in cockpit.domains if domain.instrumented)

    penalty = 0
    for domain in measured:
        points = weights.for_domain(domain.name)

        if points is None:
            raise ValueError(
                f"OPS-0008 declares no weight for domain {domain.name!r}; "
                f"every domain a cockpit names must have a declared weight"
            )

        penalty += len(domain.findings) * points

    value = max(0, 100 - penalty)

    if value >= 90:
        bucket = EXCELLENT
    elif value < 75:
        bucket = ACTION_REQUIRED
    else:
        bucket = TO_WATCH

    return HealthScore(
        value=value,
        measured_domains=len(measured),
        total_domains=len(cockpit.domains),
        bucket=bucket,
    )
