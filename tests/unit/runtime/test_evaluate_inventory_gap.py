"""
`evaluate_inventory_gap` — the Écarts-d'inventaire-domain analogue of
`evaluate_uncovered_state`, citing all four `OPS-0004` qualifications
the owner confirmed for 1.6 tranche 3's own seventh reference case
(2026-09-30).
"""

from aistack.contracts.inventory_gap import (
    DECLARED_UNDISCOVERED,
    DISCOVERED_UNDECLARED,
    InventoryGap,
)
from aistack.contracts.runtime_finding import CitedReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.runtime.evaluate_inventory_gap import (
    DEPLOYMENT_MISCONFIGURATION,
    ENERGY_INEFFICIENCY,
    INVENTORY_GAP_QUALIFICATIONS,
    INVENTORY_GAP_SOURCE,
    SUSTAINABILITY_ANOMALY,
    TECHNICAL_DEBT,
    evaluate_inventory_gap,
)


def discovered_gap() -> InventoryGap:
    return InventoryGap(
        kind=DISCOVERED_UNDECLARED, container="mystery", host="GIGABYTE"
    )


def declared_gap() -> InventoryGap:
    return InventoryGap(
        kind=DECLARED_UNDISCOVERED, container="wordpress", service="WordPress"
    )


def test_no_gaps_yields_no_findings():
    assert evaluate_inventory_gap([]) == ()


def test_a_gap_is_qualified_with_all_four_terms():
    findings = evaluate_inventory_gap([discovered_gap()])

    assert len(findings) == 1
    assert findings[0].qualifications == INVENTORY_GAP_QUALIFICATIONS
    assert findings[0].qualifications == (
        TECHNICAL_DEBT,
        DEPLOYMENT_MISCONFIGURATION,
        ENERGY_INEFFICIENCY,
        SUSTAINABILITY_ANOMALY,
    )


def test_a_discovered_undeclared_finding_is_subject_to_the_container():
    findings = evaluate_inventory_gap([discovered_gap()])

    assert findings[0].subject == "mystery"
    assert "mystery" in findings[0].interpretation
    assert "GIGABYTE" in findings[0].interpretation


def test_a_declared_undiscovered_finding_is_subject_to_the_service():
    findings = evaluate_inventory_gap([declared_gap()])

    assert findings[0].subject == "WordPress"
    assert "WordPress" in findings[0].interpretation
    assert "wordpress" in findings[0].interpretation


def test_the_finding_cites_ops_0004_as_its_signature():
    findings = evaluate_inventory_gap([discovered_gap()])

    assert findings[0].signature == "OPS-0004"


def test_the_confidence_reflects_a_measured_reading():
    findings = evaluate_inventory_gap([discovered_gap()])

    assert findings[0].confidence == "Measured"


def test_the_finding_starts_ungrounded_like_any_other():
    findings = evaluate_inventory_gap([discovered_gap()])

    assert findings[0].grounding == UNDECLARED


def test_the_evidence_cites_the_inventory_gap_source_and_the_gap_itself():
    gap = discovered_gap()
    findings = evaluate_inventory_gap([gap])

    evidence = findings[0].evidence
    assert len(evidence) == 1
    assert isinstance(evidence[0], CitedReading)
    assert evidence[0].provider == INVENTORY_GAP_SOURCE
    assert evidence[0].reading == gap


def test_one_finding_per_gap_across_both_directions():
    findings = evaluate_inventory_gap([discovered_gap(), declared_gap()])

    assert {f.subject for f in findings} == {"mystery", "WordPress"}
    assert all(f.qualifications == INVENTORY_GAP_QUALIFICATIONS for f in findings)


def test_a_discovered_undeclared_gap_with_no_known_host_still_reads_clearly():
    findings = evaluate_inventory_gap(
        [InventoryGap(kind=DISCOVERED_UNDECLARED, container="mystery")]
    )

    assert "this host" in findings[0].interpretation
