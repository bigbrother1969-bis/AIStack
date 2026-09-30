"""
`evaluate_uncovered_state` — the État-persistant-domain analogue of
`evaluate_pra_tests`, citing all four `OPS-0004` qualifications the
owner confirmed for 1.6 tranche 2's own sixth reference case
(2026-09-30).
"""

from __future__ import annotations

from aistack.contracts.backup_strategy_declaration import BackupStrategyDeclaration
from aistack.contracts.runtime_finding import CitedReading
from aistack.contracts.uncovered_state_gap import UncoveredStateGap
from aistack.contracts.undeclared import UNDECLARED
from aistack.runtime.evaluate_uncovered_state import (
    BACKUP_STRATEGY_SOURCE,
    DEPLOYMENT_MISCONFIGURATION,
    ENERGY_INEFFICIENCY,
    SUSTAINABILITY_ANOMALY,
    TECHNICAL_DEBT,
    UNCOVERED_STATE_QUALIFICATIONS,
    evaluate_uncovered_state,
)

SERVICE = "nextcloud"


def uncovered_gap(service: str = SERVICE) -> UncoveredStateGap:
    return UncoveredStateGap(
        declaration=BackupStrategyDeclaration(
            service=service, host="GIGABYTE", has_state=True
        )
    )


def test_no_gaps_yields_no_findings():
    assert evaluate_uncovered_state([]) == ()


def test_a_gap_is_qualified_with_all_four_terms():
    """
    All four qualifications the owner confirmed 2026-09-30 — the
    second reference case, after GPU, to carry the complete
    vocabulary — always cited together.
    """

    findings = evaluate_uncovered_state([uncovered_gap()])

    assert len(findings) == 1
    assert findings[0].qualifications == UNCOVERED_STATE_QUALIFICATIONS
    assert findings[0].qualifications == (
        TECHNICAL_DEBT,
        DEPLOYMENT_MISCONFIGURATION,
        ENERGY_INEFFICIENCY,
        SUSTAINABILITY_ANOMALY,
    )


def test_the_finding_subject_is_the_gap_service():
    findings = evaluate_uncovered_state([uncovered_gap(service=SERVICE)])

    assert findings[0].subject == SERVICE


def test_the_finding_cites_ops_0004_as_its_signature():
    findings = evaluate_uncovered_state([uncovered_gap()])

    assert findings[0].signature == "OPS-0004"


def test_the_confidence_reflects_a_measured_reading():
    findings = evaluate_uncovered_state([uncovered_gap()])

    assert findings[0].confidence == "Measured"


def test_the_finding_starts_ungrounded_like_any_other():
    findings = evaluate_uncovered_state([uncovered_gap()])

    assert findings[0].grounding == UNDECLARED


def test_the_evidence_cites_the_backup_strategy_source_and_the_declaration():
    gap = uncovered_gap()
    findings = evaluate_uncovered_state([gap])

    evidence = findings[0].evidence
    assert len(evidence) == 1
    assert isinstance(evidence[0], CitedReading)
    assert evidence[0].provider == BACKUP_STRATEGY_SOURCE
    assert evidence[0].reading == gap.declaration


def test_the_interpretation_names_the_service():
    findings = evaluate_uncovered_state([uncovered_gap()])

    assert SERVICE in findings[0].interpretation


def test_one_finding_per_gap():
    findings = evaluate_uncovered_state(
        [uncovered_gap(service="a"), uncovered_gap(service="b")]
    )

    assert {f.subject for f in findings} == {"a", "b"}
    assert all(f.qualifications == UNCOVERED_STATE_QUALIFICATIONS for f in findings)
