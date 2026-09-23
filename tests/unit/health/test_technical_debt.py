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
    findings = (a_finding("a", qualified=False), a_finding("b", qualified=False))

    score = compute_technical_debt_score(findings, weight=15)

    assert score.value == 100
    assert score.findings == ()


def test_one_qualified_finding_subtracts_the_weight():
    findings = (a_finding("a"),)

    score = compute_technical_debt_score(findings, weight=15)

    assert score.value == 85  # 100 - 15
    assert score.findings == findings


def test_qualified_findings_are_cumulative():
    findings = (a_finding("a"), a_finding("b"), a_finding("c"))

    score = compute_technical_debt_score(findings, weight=15)

    assert score.value == 55  # 100 - 3*15
    assert len(score.findings) == 3


def test_a_mix_of_qualified_and_unqualified_counts_only_the_qualified():
    findings = (a_finding("a"), a_finding("b", qualified=False))

    score = compute_technical_debt_score(findings, weight=15)

    assert score.value == 85
    assert score.findings == (findings[0],)


def test_the_score_never_drops_below_zero():
    findings = tuple(a_finding(str(i)) for i in range(10))

    score = compute_technical_debt_score(findings, weight=15)

    assert score.value == 0
    assert score.bucket == ACTION_REQUIRED


def test_bucket_boundaries_match_the_health_score():
    # >= 90 excellent
    assert compute_technical_debt_score(
        tuple(a_finding(str(i)) for i in range(10)), weight=1
    ).value == 90
    assert compute_technical_debt_score(
        tuple(a_finding(str(i)) for i in range(10)), weight=1
    ).bucket == EXCELLENT

    # 75 <= score < 90 is à surveiller
    assert compute_technical_debt_score(
        tuple(a_finding(str(i)) for i in range(11)), weight=1
    ).bucket == TO_WATCH  # 89
    assert compute_technical_debt_score(
        tuple(a_finding(str(i)) for i in range(25)), weight=1
    ).value == 75
    assert compute_technical_debt_score(
        tuple(a_finding(str(i)) for i in range(25)), weight=1
    ).bucket == TO_WATCH

    # < 75 is action requise
    assert compute_technical_debt_score(
        tuple(a_finding(str(i)) for i in range(26)), weight=1
    ).value == 74
    assert compute_technical_debt_score(
        tuple(a_finding(str(i)) for i in range(26)), weight=1
    ).bucket == ACTION_REQUIRED
