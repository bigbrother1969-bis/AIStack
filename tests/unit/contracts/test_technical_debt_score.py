from __future__ import annotations

import pytest

from aistack.contracts.health_score import ACTION_REQUIRED, EXCELLENT, TO_WATCH
from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.technical_debt_score import (
    TECHNICAL_DEBT_QUALIFICATION,
    TechnicalDebtScore,
)


def a_finding(qualifications: tuple[str, ...] = (TECHNICAL_DEBT_QUALIFICATION,)) -> RuntimeFinding:
    return RuntimeFinding(
        subject="gluetun",
        signature="OPS-0004",
        interpretation="restarting",
        remediation="investigate boot order",
        confidence="Measured",
        grounding="unknown",
        evidence=(
            CitedReading(
                provider="aistack.provider.storage",
                reading=StorageReading(
                    mount="/", total_bytes=100, used_bytes=99, free_bytes=1
                ),
            ),
        ),
        qualifications=qualifications,
    )


def test_a_score_above_100_is_refused():
    with pytest.raises(ValueError, match="within 0-100"):
        TechnicalDebtScore(value=101, findings=(), bucket=EXCELLENT)


def test_a_negative_score_is_refused():
    with pytest.raises(ValueError, match="within 0-100"):
        TechnicalDebtScore(value=-1, findings=(), bucket=EXCELLENT)


def test_a_finding_not_qualified_technical_debt_is_refused():
    unqualified = a_finding(qualifications=("OPS-0004/deployment-misconfiguration",))

    with pytest.raises(ValueError, match="not qualified"):
        TechnicalDebtScore(value=85, findings=(unqualified,), bucket=TO_WATCH)


def test_an_unknown_bucket_is_refused():
    with pytest.raises(ValueError, match="unknown technical-debt-score bucket"):
        TechnicalDebtScore(value=100, findings=(), bucket="parfait")


def test_a_valid_score_is_accepted():
    finding = a_finding()

    score = TechnicalDebtScore(value=85, findings=(finding,), bucket=TO_WATCH)

    assert score.value == 85
    assert score.findings == (finding,)
    assert score.bucket == TO_WATCH


def test_each_declared_bucket_is_accepted():
    for bucket in (EXCELLENT, TO_WATCH, ACTION_REQUIRED):
        TechnicalDebtScore(value=50, findings=(), bucket=bucket)


def test_no_findings_is_accepted():
    score = TechnicalDebtScore(value=100, findings=(), bucket=EXCELLENT)

    assert score.findings == ()
