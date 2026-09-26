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

    Each instrumented domain first scores itself exactly as before:
    `domain_score = max(0, 100 − findings × its own weight)` — findings
    within one domain stay cumulative, the owner's own explicit choice
    over a flat per-domain penalty, unchanged by this function. The
    overall score is then the *weighted average* of those per-domain
    scores — weighted by each domain's own `OPS-0008` points — rather
    than a global subtraction, the owner's 2026-09-26 correction to the
    2026-09-11 formula: one domain saturating its own penalty (its
    score floored at 0) no longer floors every other domain's clean
    result along with it, while still counting for its full declared
    share of the total. A domain not instrumented contributes nothing
    and is excluded from both the numerator and the denominator — the
    same `FDN-0003` Article 12 absence `HealthDomain` itself already
    enforces, never smoothed into either a penalty or a clean pass
    here. When no domain is instrumented at all there is nothing to
    average, so the result is 100 (unchanged from the prior formula's
    own `max(0, 100 − 0)` in that same case) rather than a division by
    zero.

    Raises if a cockpit names a domain `weights` has no entry for —
    `PLAN-J7`'s domain vocabulary is closed at four, and `OPS-0008` is
    expected to cover it completely; a domain missing its own weight
    is a configuration defect, not a governed absence, so this does
    not degrade quietly the way a missing threshold file does.
    """

    measured = tuple(domain for domain in cockpit.domains if domain.instrumented)

    weighted_domain_scores: list[tuple[int, int]] = []  # (weight, domain_score)
    for domain in measured:
        points = weights.for_domain(domain.name)

        if points is None:
            raise ValueError(
                f"OPS-0008 declares no weight for domain {domain.name!r}; "
                f"every domain a cockpit names must have a declared weight"
            )

        domain_score = max(0, 100 - len(domain.findings) * points)
        weighted_domain_scores.append((points, domain_score))

    if weighted_domain_scores:
        total_weight = sum(points for points, _ in weighted_domain_scores)
        weighted_sum = sum(
            points * domain_score for points, domain_score in weighted_domain_scores
        )
        value = round(weighted_sum / total_weight)
    else:
        value = 100

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
