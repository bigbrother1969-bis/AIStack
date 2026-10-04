from __future__ import annotations

from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.technical_debt_score import TECHNICAL_DEBT_QUALIFICATION
from aistack.health.technical_debt import compute_technical_debt_score


def a_finding(subject: str = "gluetun", qualified: bool = True) -> RuntimeFinding:
    return RuntimeFinding(
        subject=subject,
        signature="OPS-0004",
        interpretation="restarting",
        remediation="investigate boot order",
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
        qualifications=(
            (TECHNICAL_DEBT_QUALIFICATION,)
            if qualified
            else ("OPS-0004/deployment-misconfiguration",)
        ),
    )


def test_no_findings_scores_100_excellent():
    score = compute_technical_debt_score((), weight=15)

    assert score.value == 100
    assert score.bucket == EXCELLENT
    assert score.findings == ()


def test_findings_not_qualified_technical_debt_are_excluded():
    domains = ((a_finding("a", qualified=False), a_finding("b", qualified=False)),)

    score = compute_technical_debt_score(domains, weight=15)

    assert score.value == 100
    assert score.findings == ()


def test_one_domain_with_debt_subtracts_the_weight_once():
    domains = ((a_finding("a"), a_finding("b"), a_finding("c")),)

    score = compute_technical_debt_score(domains, weight=15)

    assert score.value == 85  # 100 - 15, however many findings
    assert len(score.findings) == 3


def test_each_domain_with_debt_costs_the_weight():
    domains = ((a_finding("a"),), (), (a_finding("b"), a_finding("c")))

    score = compute_technical_debt_score(domains, weight=15)

    assert score.value == 70  # 100 - 2*15
    assert len(score.findings) == 3


def test_gigabyte_2026_10_04_four_restore_tests_and_seven_gaps_score_70():
    """Measured on GIGABYTE: 11 debt findings in two domains clamped the
    old per-finding score to 0; per domain it reads 70."""

    pra = tuple(a_finding(f"pra{i}") for i in range(4))
    gaps = tuple(a_finding(f"gap{i}") for i in range(7))

    score = compute_technical_debt_score(((), (), (), (), pra, (), gaps), weight=15)

    assert score.value == 70
    assert score.bucket == ACTION_REQUIRED
    assert len(score.findings) == 11


def test_a_domain_of_unqualified_findings_costs_nothing():
    domains = ((a_finding("a"),), (a_finding("b", qualified=False),))

    score = compute_technical_debt_score(domains, weight=15)

    assert score.value == 85
    assert score.findings == (domains[0][0],)


def test_the_score_never_drops_below_zero():
    domains = tuple((a_finding(str(i)),) for i in range(10))

    score = compute_technical_debt_score(domains, weight=15)

    assert score.value == 0
    assert score.bucket == ACTION_REQUIRED


def test_bucket_boundaries_match_the_health_score():
    def score(domains: int):
        return compute_technical_debt_score(tuple((a_finding(str(i)),) for i in range(domains)), weight=1)

    assert score(10).value == 90 and score(10).bucket == EXCELLENT
    assert score(11).bucket == TO_WATCH  # 89
    assert score(25).value == 75 and score(25).bucket == TO_WATCH
    assert score(26).value == 74 and score(26).bucket == ACTION_REQUIRED
