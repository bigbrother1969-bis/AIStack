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
    Compute the `HealthScore` of a cockpit from the `OPS-0008` weights.

    Each instrumented domain scores `max(0, 100 - findings × weight)`; the
    overall score is the average of those scores weighted by each domain's
    weight, so one saturated domain does not floor the others.
    Uninstrumented domains are left out entirely; with none instrumented
    the score is 100. A domain with no declared weight raises `ValueError`:
    that is a configuration defect. Pure.
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
