"""
`evaluate_storage` — the storage-capacity analogue of `evaluate`,
citing `OPS-0004`'s `deployment misconfiguration` from a
`StorageShortage` already confirmed by `find_storage_shortage`.
"""

from __future__ import annotations

from aistack.contracts.runtime_finding import CitedReading
from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.storage_shortage import StorageShortage
from aistack.contracts.storage_threshold import FREE_BYTES, PERCENT_USED
from aistack.contracts.undeclared import UNDECLARED
from aistack.runtime.evaluate_storage import (
    DEPLOYMENT_MISCONFIGURATION,
    STORAGE_PROVIDER,
    evaluate_storage,
)


def free_bytes_shortage(
    mount: str = "/", free_bytes: int = 10 * 1024**3
) -> StorageShortage:
    total = 212 * 1024**3
    return StorageShortage(
        reading=StorageReading(
            mount=mount,
            total_bytes=total,
            used_bytes=total - free_bytes,
            free_bytes=free_bytes,
        ),
        threshold_kind=FREE_BYTES,
        threshold_value=20 * 1024**3,
    )


def percent_used_shortage(mount: str = "/media/Films") -> StorageShortage:
    return StorageShortage(
        reading=StorageReading(
            mount=mount, total_bytes=100, used_bytes=92, free_bytes=8
        ),
        threshold_kind=PERCENT_USED,
        threshold_value=90.0,
    )


def test_no_shortages_yields_no_findings():

    assert evaluate_storage([]) == ()


def test_a_shortage_is_qualified_deployment_misconfiguration():

    findings = evaluate_storage([free_bytes_shortage()])

    assert len(findings) == 1
    assert findings[0].qualifications == (DEPLOYMENT_MISCONFIGURATION,)


def test_the_finding_subject_is_the_short_mount():

    findings = evaluate_storage([free_bytes_shortage(mount="/")])

    assert findings[0].subject == "/"


def test_the_finding_cites_ops_0004_as_its_signature():

    findings = evaluate_storage([free_bytes_shortage()])

    assert findings[0].signature == "OPS-0004"


def test_the_confidence_reflects_a_measured_reading():

    findings = evaluate_storage([free_bytes_shortage()])

    assert findings[0].confidence == "Measured"


def test_the_finding_starts_ungrounded_like_any_other():

    findings = evaluate_storage([free_bytes_shortage()])

    assert findings[0].grounding == UNDECLARED


def test_the_evidence_cites_the_storage_provider_and_the_reading():

    shortage = free_bytes_shortage()
    findings = evaluate_storage([shortage])

    evidence = findings[0].evidence
    assert len(evidence) == 1
    assert isinstance(evidence[0], CitedReading)
    assert evidence[0].provider == STORAGE_PROVIDER
    assert evidence[0].reading == shortage.reading


def test_a_free_bytes_interpretation_states_gb_free_and_the_threshold():

    findings = evaluate_storage([free_bytes_shortage()])

    interpretation = findings[0].interpretation
    assert "10.0 GB free" in interpretation
    assert "20.0 GB" in interpretation
    assert DEPLOYMENT_MISCONFIGURATION in interpretation


def test_a_percent_used_interpretation_states_percent_and_the_threshold():

    findings = evaluate_storage([percent_used_shortage()])

    interpretation = findings[0].interpretation
    assert "92.0%" in interpretation
    assert "90.0%" in interpretation


def test_one_finding_per_shortage():

    findings = evaluate_storage(
        [free_bytes_shortage(mount="/"), percent_used_shortage(mount="/media/Films")]
    )

    assert {f.subject for f in findings} == {"/", "/media/Films"}
    assert all(
        f.qualifications == (DEPLOYMENT_MISCONFIGURATION,) for f in findings
    )
