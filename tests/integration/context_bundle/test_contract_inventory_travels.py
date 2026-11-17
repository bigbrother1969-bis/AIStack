from datetime import datetime
from pathlib import Path
import json
import zipfile

from aistack.conformance.inventory import take_inventory
from aistack.context_bundle.export.zip_bundle_exporter import (
    ZipBundleExporter,
)
from aistack.contracts.context_bundle import ContextBundle
from aistack.integrity.bundle_reader import read_bundle
from aistack.integrity.checks.contract_debt import ContractDebtCheck


NOW = datetime(2026, 8, 22, 12, 0, 0)


def export(tmp_path: Path, inventory) -> Path:
    """
    Write a projection the way the pipeline writes one.

    STD-0002: the output goes to `tmp_path`, never over the
    repository's published projection.
    """

    bundle = ContextBundle(
        id="test-bundle",
        title="Test",
        generated_at=NOW,
        source_commit="abc1234",
        contract_inventory=inventory,
    )

    path = tmp_path / "bundle.zip"

    ZipBundleExporter().export(bundle, path)

    return path


def test_the_inventory_survives_the_projection(tmp_path):
    """
    The end-to-end path, and the one nothing covered: measure,
    write to the archive, read it back, publish it.

    Its absence was found by mutation on 2026-08-22 — removing
    the write, removing the read, or measuring nothing at
    generation all left the suite green. A publication chain no
    test walks is a chain that can stop publishing in silence,
    which is the whole failure `contract-debt` exists to prevent.
    """

    measured = take_inventory()

    restored = read_bundle(export(tmp_path, measured))

    assert restored.contract_inventory is not None
    assert restored.contract_inventory == measured
    assert restored.contract_inventory.orphans == measured.orphans


def test_the_archive_carries_the_inventory_as_its_own_entry(tmp_path):

    with zipfile.ZipFile(export(tmp_path, take_inventory())) as archive:

        assert "contract-inventory.json" in archive.namelist()

        payload = json.loads(archive.read("contract-inventory.json"))

    assert payload["package"] == "aistack"
    assert payload["contracts"]


def test_a_bundle_without_a_measurement_carries_no_entry(tmp_path):
    """
    An empty file would be indistinguishable from a heritage with
    no contracts. The absent entry is how this format says the
    measurement was not taken.
    """

    with zipfile.ZipFile(export(tmp_path, None)) as archive:
        assert "contract-inventory.json" not in archive.namelist()

    assert read_bundle(export(tmp_path, None)).contract_inventory is None


def test_the_check_publishes_what_the_projection_carries(tmp_path):
    """
    The last link: what a consumer holding only the archive can
    state about the debt of the heritage it received.
    """

    restored = read_bundle(export(tmp_path, take_inventory()))

    findings = ContractDebtCheck().evaluate(restored)

    assert findings
    assert findings[0].affected == len(take_inventory().orphans)
    assert findings[0].subjects


def test_a_loose_bundle_json_carries_no_inventory(tmp_path):
    """
    The inventory travels as a separate archive entry, so a
    consumer holding the loose `bundle.json` gets `None` — and
    the check says *undeclared*, never zero.
    """

    archive_path = export(tmp_path, take_inventory())

    with zipfile.ZipFile(archive_path) as archive:
        loose = tmp_path / "bundle.json"
        loose.write_bytes(archive.read("bundle.json"))

    restored = read_bundle(loose)

    assert restored.contract_inventory is None

    findings = ContractDebtCheck().evaluate(restored)

    assert "undeclared, not zero" in findings[0].summary
