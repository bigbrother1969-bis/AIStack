import pytest

from aistack.contracts.health_score import (
    ACTION_REQUIRED,
    EXCELLENT,
    TO_WATCH,
    DomainWeight,
    HealthScore,
    HealthScoreWeights,
)

# --------------------------------------------------------------------
# DomainWeight
# --------------------------------------------------------------------


def test_a_weight_names_no_domain_is_refused():
    with pytest.raises(ValueError, match="names no domain"):
        DomainWeight(domain="", points=10)


def test_a_non_positive_weight_is_refused():
    with pytest.raises(ValueError, match="non-positive weight"):
        DomainWeight(domain="Stockage", points=0)


def test_a_negative_weight_is_refused():
    with pytest.raises(ValueError, match="non-positive weight"):
        DomainWeight(domain="Stockage", points=-5)


def test_a_valid_weight_is_accepted():
    weight = DomainWeight(domain="Stockage", points=10)

    assert weight.domain == "Stockage"
    assert weight.points == 10


# --------------------------------------------------------------------
# HealthScoreWeights
# --------------------------------------------------------------------


def test_for_domain_returns_the_matching_entry():
    weights = HealthScoreWeights(weights=(DomainWeight(domain="Stockage", points=10),))

    assert weights.for_domain("Stockage") == 10


def test_for_domain_returns_none_for_an_undeclared_domain():
    weights = HealthScoreWeights(weights=())

    assert weights.for_domain("GPU") is None


# --------------------------------------------------------------------
# HealthScore
# --------------------------------------------------------------------


def test_a_score_above_100_is_refused():
    with pytest.raises(ValueError, match="within 0-100"):
        HealthScore(value=101, measured_domains=1, total_domains=1, bucket=EXCELLENT)


def test_a_negative_score_is_refused():
    with pytest.raises(ValueError, match="within 0-100"):
        HealthScore(value=-1, measured_domains=1, total_domains=1, bucket=EXCELLENT)


def test_negative_domain_counts_are_refused():
    with pytest.raises(ValueError, match="negative domains"):
        HealthScore(value=100, measured_domains=-1, total_domains=1, bucket=EXCELLENT)


def test_measuring_more_domains_than_named_is_refused():
    with pytest.raises(ValueError, match="more domains than it names"):
        HealthScore(value=100, measured_domains=5, total_domains=4, bucket=EXCELLENT)


def test_an_unknown_bucket_is_refused():
    with pytest.raises(ValueError, match="unknown health-score bucket"):
        HealthScore(value=100, measured_domains=4, total_domains=4, bucket="parfait")


def test_a_valid_score_is_accepted():
    score = HealthScore(value=82, measured_domains=3, total_domains=4, bucket=TO_WATCH)

    assert score.value == 82
    assert score.measured_domains == 3
    assert score.total_domains == 4
    assert score.bucket == TO_WATCH


def test_each_declared_bucket_is_accepted():
    for bucket in (EXCELLENT, TO_WATCH, ACTION_REQUIRED):
        HealthScore(value=50, measured_domains=1, total_domains=1, bucket=bucket)
