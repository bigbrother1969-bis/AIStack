"""
`evaluate_backup` — the Sauvegarde/PRA analogue of `evaluate_storage`
and `evaluate_services`, citing `OPS-0004`'s `technical debt` and
`deployment misconfiguration` from a `BackupGap` already confirmed by
`find_backup_gaps`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aistack.contracts.backup_gap import MISSING, STALE, BackupGap
from aistack.contracts.backup_reading import BackupReading
from aistack.contracts.runtime_finding import CitedReading
from aistack.contracts.undeclared import UNDECLARED
from aistack.runtime.evaluate_backup import (
    BACKUP_GAP_QUALIFICATIONS,
    BACKUP_PROVIDER,
    DEPLOYMENT_MISCONFIGURATION,
    TECHNICAL_DEBT,
    evaluate_backup,
)

PATH = "/media/BACKUP/persiaut-consulting/wordpress/"


def missing_gap(path: str = PATH) -> BackupGap:
    return BackupGap(
        reading=BackupReading(path=path, observed_at=datetime.now(timezone.utc)),
        max_age_hours=168.0,
        reason=MISSING,
    )


def stale_gap(age_hours: float = 200.0, path: str = PATH) -> BackupGap:
    observed_at = datetime.now(timezone.utc)
    return BackupGap(
        reading=BackupReading(
            path=path,
            observed_at=observed_at,
            newest_file_mtime=observed_at - timedelta(hours=age_hours),
        ),
        max_age_hours=168.0,
        reason=STALE,
    )


def test_no_gaps_yields_no_findings():

    assert evaluate_backup([]) == ()


def test_a_gap_is_qualified_technical_debt_and_deployment_misconfiguration():

    findings = evaluate_backup([missing_gap()])

    assert len(findings) == 1
    assert findings[0].qualifications == BACKUP_GAP_QUALIFICATIONS
    assert findings[0].qualifications == (
        TECHNICAL_DEBT,
        DEPLOYMENT_MISCONFIGURATION,
    )


def test_the_finding_subject_is_the_gap_path():

    findings = evaluate_backup([missing_gap(path=PATH)])

    assert findings[0].subject == PATH


def test_the_finding_cites_ops_0004_as_its_signature():

    findings = evaluate_backup([missing_gap()])

    assert findings[0].signature == "OPS-0004"


def test_the_confidence_reflects_a_measured_reading():

    findings = evaluate_backup([missing_gap()])

    assert findings[0].confidence == "Measured"


def test_the_finding_starts_ungrounded_like_any_other():

    findings = evaluate_backup([missing_gap()])

    assert findings[0].grounding == UNDECLARED


def test_the_evidence_cites_the_backup_provider_and_the_reading():

    gap = missing_gap()
    findings = evaluate_backup([gap])

    evidence = findings[0].evidence
    assert len(evidence) == 1
    assert isinstance(evidence[0], CitedReading)
    assert evidence[0].provider == BACKUP_PROVIDER
    assert evidence[0].reading == gap.reading


def test_a_missing_interpretation_states_no_backup_file_found():

    findings = evaluate_backup([missing_gap()])

    interpretation = findings[0].interpretation
    assert "no backup file" in interpretation
    assert TECHNICAL_DEBT not in interpretation  # interpretation names terms, not citations
    assert "technical debt" in interpretation
    assert "deployment misconfiguration" in interpretation


def test_a_stale_interpretation_states_the_age_and_threshold():

    findings = evaluate_backup([stale_gap(age_hours=200.0)])

    interpretation = findings[0].interpretation
    assert "200.0 hours" in interpretation
    assert "168.0 hours" in interpretation


def test_one_finding_per_gap():

    findings = evaluate_backup(
        [missing_gap(path="/a/"), stale_gap(path="/b/")]
    )

    assert {f.subject for f in findings} == {"/a/", "/b/"}
    assert all(f.qualifications == BACKUP_GAP_QUALIFICATIONS for f in findings)
