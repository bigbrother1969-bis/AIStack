from pathlib import Path

from aistack.transaction.manifest import ManifestBuilder
from aistack.transaction.models import Transaction


def test_manifest_builder():
    tx = Transaction(
        transaction_id="KT-000003",
        definition_id="code.patch",
        payload=Path("payload.zip"),
    )

    manifest = ManifestBuilder().build(tx)

    assert manifest["transaction_id"] == "KT-000003"
    assert manifest["definition_id"] == "code.patch"
    assert manifest["payload"] == "payload.zip"
