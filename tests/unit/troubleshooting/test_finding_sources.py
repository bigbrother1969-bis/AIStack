"""Where the troubleshooting assistant reads the last network discovery (UAT, 2026-10-09)."""

from __future__ import annotations

from tests.conftest import REFERENCE_DEFINITIONS as REFERENCE

from pathlib import Path

from aistack.troubleshooting import findings


def test_the_data_directory_of_the_working_directory_comes_first(tmp_path: Path, monkeypatch):
    observation = tmp_path / "reports" / "generated" / "network-docker-observation.json"
    observation.parent.mkdir(parents=True)
    observation.write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert findings.FindingSources().network_docker_observation == observation


def test_without_one_the_checkout_is_read(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert findings.FindingSources().network_docker_observation == (
        findings.REPOSITORY_ROOT / "reports" / "generated" / "network-docker-observation.json"
    )


def test_a_pra_finding_cites_the_declared_mechanism_and_the_entry_to_write():
    from datetime import datetime, timezone

    from aistack.contracts.pra_test_reading import PraTestReading
    from aistack.contracts.runtime_finding import CitedReading, RuntimeFinding
    from aistack.i18n.translator import translator_for
    from aistack.troubleshooting.facts import PRA_TESTS, Declarations, guidance

    finding = RuntimeFinding(
        subject="gigabyte",
        signature="OPS-0004",
        interpretation="never tested",
        remediation="test it",
        confidence="Measured",
        grounding="OPS-0009",
        evidence=(
            CitedReading(
                provider="pra",
                reading=PraTestReading(service="gigabyte", observed_at=datetime.now(timezone.utc)),
            ),
        ),
        qualifications=("OPS-0004/technical-debt",),
    )
    t = translator_for("fr")
    declared = Declarations(
        REFERENCE / "backup_strategy.yml",
        REFERENCE / "pra_tests.yml",
        REFERENCE / "resource_priority.yml",
    )

    guide = guidance(PRA_TESTS, finding, t, declared, "test it")

    facts = {fact.label: fact.value for fact in guide.facts}
    assert facts["Dernier test"] == "jamais"
    assert facts["Observé le"].endswith(" UTC")
    assert "Clonezilla" in facts["Mécanisme déclaré"]
    assert facts["Âge maximal d'un test (jours)"] == "90"
    assert guide.snippet_file == "./config/pra_tests.yml"
    assert "  - name: gigabyte\n    last_test:\n      status: success" in guide.snippet
    # The owner's test for a host imaged by Clonezilla (2026-10-09).
    assert "chk-img-restorable" in guide.steps[0]
    assert guide.snippet.startswith("  # Vérification Clonezilla")
