"""
`evaluate_pra_tests` — the Tests-PRA-domain analogue of
`evaluate_backup`, citing `OPS-0004`'s three qualifications the owner
confirmed when `PLAN-J11` § 11.9.1's third and last named gap ("tests
PRA") was reopened, 2026-09-23.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aistack.contracts.pra_test_gap import FAILED_REASON, STALE, UNTESTED, PraTestGap
from aistack.contracts.pra_test_reading import FAILED, SUCCESS, PraTestReading
from aistack.contracts.runtime_finding import CitedReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.runtime.evaluate_pra_tests import (
    DEPLOYMENT_MISCONFIGURATION,
    PRA_TEST_GAP_QUALIFICATIONS,
    PRA_TESTS_SOURCE,
    SUSTAINABILITY_ANOMALY,
    TECHNICAL_DEBT,
    evaluate_pra_tests,
)

SERVICE = "nextcloud"


def untested_gap(service: str = SERVICE) -> PraTestGap:
    return PraTestGap(
        reading=PraTestReading(
            service=service, observed_at=datetime.now(timezone.utc)
        ),
        max_age_days=90.0,
        reason=UNTESTED,
    )


def failed_gap(service: str = SERVICE) -> PraTestGap:
    observed_at = datetime.now(timezone.utc)
    return PraTestGap(
        reading=PraTestReading(
            service=service, observed_at=observed_at, status=FAILED, tested_at=observed_at
        ),
        max_age_days=90.0,
        reason=FAILED_REASON,
    )


def stale_gap(age_days: float = 200.0, service: str = SERVICE) -> PraTestGap:
    observed_at = datetime.now(timezone.utc)
    return PraTestGap(
        reading=PraTestReading(
            service=service,
            observed_at=observed_at,
            status=SUCCESS,
            tested_at=observed_at - timedelta(days=age_days),
        ),
        max_age_days=90.0,
        reason=STALE,
    )


def test_no_gaps_yields_no_findings():

    assert evaluate_pra_tests([]) == ()


def test_a_gap_is_qualified_technical_debt_sustainability_and_misconfiguration():
    """
    The three qualifications the owner confirmed 2026-09-23 — energy
    inefficiency was examined and explicitly excluded — always cited
    together, mirroring `evaluate_services`'s own fixed vocabulary for
    its own third reference incident.
    """

    findings = evaluate_pra_tests([untested_gap()])

    assert len(findings) == 1
    assert findings[0].qualifications == PRA_TEST_GAP_QUALIFICATIONS
    assert findings[0].qualifications == (
        TECHNICAL_DEBT,
        SUSTAINABILITY_ANOMALY,
        DEPLOYMENT_MISCONFIGURATION,
    )


def test_the_finding_subject_is_the_gap_service():

    findings = evaluate_pra_tests([untested_gap(service=SERVICE)])

    assert findings[0].subject == SERVICE


def test_the_finding_cites_ops_0004_as_its_signature():

    findings = evaluate_pra_tests([untested_gap()])

    assert findings[0].signature == "OPS-0004"


def test_the_confidence_reflects_a_measured_reading():

    findings = evaluate_pra_tests([untested_gap()])

    assert findings[0].confidence == "Measured"


def test_the_finding_starts_ungrounded_like_any_other():

    findings = evaluate_pra_tests([untested_gap()])

    assert findings[0].grounding == UNDECLARED


def test_the_evidence_cites_the_pra_tests_source_and_the_reading():

    gap = untested_gap()
    findings = evaluate_pra_tests([gap])

    evidence = findings[0].evidence
    assert len(evidence) == 1
    assert isinstance(evidence[0], CitedReading)
    assert evidence[0].provider == PRA_TESTS_SOURCE
    assert evidence[0].reading == gap.reading


def test_an_untested_interpretation_states_never_tested():

    findings = evaluate_pra_tests([untested_gap()])

    interpretation = findings[0].interpretation
    assert "never had a restore test" in interpretation


def test_a_failed_interpretation_states_the_failure():

    findings = evaluate_pra_tests([failed_gap()])

    interpretation = findings[0].interpretation
    assert "failed" in interpretation


def test_a_stale_interpretation_states_the_age_and_threshold():

    findings = evaluate_pra_tests([stale_gap(age_days=200.0)])

    interpretation = findings[0].interpretation
    assert "200.0" in interpretation
    assert "90.0" in interpretation


def test_one_finding_per_gap():

    findings = evaluate_pra_tests(
        [untested_gap(service="a"), stale_gap(service="b")]
    )

    assert {f.subject for f in findings} == {"a", "b"}
    assert all(f.qualifications == PRA_TEST_GAP_QUALIFICATIONS for f in findings)
