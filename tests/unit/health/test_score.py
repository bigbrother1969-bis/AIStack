from __future__ import annotations

import pytest

from aistack.contracts.health_score import (
    ACTION_REQUIRED,
    EXCELLENT,
    TO_WATCH,
    DomainWeight,
    HealthScoreWeights,
)
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_reading import StorageReading
from aistack.health.cockpit import HealthCockpit, HealthDomain
from aistack.health.score import compute_health_score

WEIGHTS = HealthScoreWeights(
    weights=(
        DomainWeight(domain="Stockage", points=10),
        DomainWeight(domain="Services", points=15),
        DomainWeight(domain="Sauvegarde / PRA", points=25),
        DomainWeight(domain="GPU", points=8),
    )
)


def a_finding(subject: str = "/") -> RuntimeFinding:
    return RuntimeFinding(
        subject=subject,
        signature="OPS-0004",
        interpretation="short on space",
        remediation="free some up",
        confidence="Measured",
        grounding="unknown",
        evidence=(
            CitedReading(
                provider="aistack.provider.storage",
                reading=StorageReading(
                    mount=subject, total_bytes=100, used_bytes=99, free_bytes=1
                ),
            ),
        ),
        qualifications=("OPS-0004/deployment-misconfiguration",),
    )


def test_a_fully_clean_cockpit_scores_100_excellent():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True),
            HealthDomain(name="Services", instrumented=True),
            HealthDomain(name="Sauvegarde / PRA", instrumented=True),
            HealthDomain(name="GPU", instrumented=True),
        )
    )

    score = compute_health_score(cockpit, WEIGHTS)

    assert score.value == 100
    assert score.bucket == EXCELLENT
    assert score.measured_domains == 4
    assert score.total_domains == 4


def test_one_finding_subtracts_its_own_domain_weight():
    cockpit = HealthCockpit(
        domains=(HealthDomain(name="Stockage", instrumented=True, findings=(a_finding(),)),)
    )

    score = compute_health_score(cockpit, WEIGHTS)

    assert score.value == 90  # 100 - 10


def test_findings_within_one_domain_are_cumulative():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="GPU",
                instrumented=True,
                findings=(a_finding("temp"), a_finding("util"), a_finding("mem")),
            ),
        )
    )

    score = compute_health_score(cockpit, WEIGHTS)

    assert score.value == 76  # 100 - 3*8


def test_a_not_instrumented_domain_is_excluded_not_penalized():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(name="Stockage", instrumented=True),
            HealthDomain(name="GPU", instrumented=False, note="pas encore"),
        )
    )

    score = compute_health_score(cockpit, WEIGHTS)

    assert score.value == 100
    assert score.measured_domains == 1
    assert score.total_domains == 2


def test_the_score_never_drops_below_zero():
    cockpit = HealthCockpit(
        domains=(
            HealthDomain(
                name="Sauvegarde / PRA",
                instrumented=True,
                findings=tuple(a_finding(str(i)) for i in range(10)),
            ),
        )
    )

    score = compute_health_score(cockpit, WEIGHTS)

    assert score.value == 0
    assert score.bucket == ACTION_REQUIRED


def test_a_domain_the_weights_do_not_declare_raises():
    cockpit = HealthCockpit(domains=(HealthDomain(name="Raspberry", instrumented=True),))

    with pytest.raises(ValueError, match="no weight for domain"):
        compute_health_score(cockpit, WEIGHTS)


_ONE_POINT_WEIGHTS = HealthScoreWeights(
    weights=(DomainWeight(domain="Stockage", points=1),)
)


def _cockpit_with_findings(count: int) -> HealthCockpit:
    return HealthCockpit(
        domains=(
            HealthDomain(
                name="Stockage",
                instrumented=True,
                findings=tuple(a_finding(str(i)) for i in range(count)),
            ),
        )
    )


def test_bucket_boundaries_are_declared_by_the_owner():
    # >= 90 is excellent
    assert (
        compute_health_score(_cockpit_with_findings(10), _ONE_POINT_WEIGHTS).value
        == 90
    )
    assert (
        compute_health_score(_cockpit_with_findings(10), _ONE_POINT_WEIGHTS).bucket
        == EXCELLENT
    )

    # 75 <= score < 90 is à surveiller, at both edges
    assert (
        compute_health_score(_cockpit_with_findings(11), _ONE_POINT_WEIGHTS).bucket
        == TO_WATCH
    )  # 89
    assert (
        compute_health_score(_cockpit_with_findings(25), _ONE_POINT_WEIGHTS).value
        == 75
    )
    assert (
        compute_health_score(_cockpit_with_findings(25), _ONE_POINT_WEIGHTS).bucket
        == TO_WATCH
    )

    # < 75 is action requise
    assert (
        compute_health_score(_cockpit_with_findings(26), _ONE_POINT_WEIGHTS).value
        == 74
    )
    assert (
        compute_health_score(_cockpit_with_findings(26), _ONE_POINT_WEIGHTS).bucket
        == ACTION_REQUIRED
    )
