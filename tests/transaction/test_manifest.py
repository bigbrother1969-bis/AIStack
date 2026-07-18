from pathlib import Path

from aistack.transaction.manifest import ManifestBuilder
from aistack.transaction.models import Transaction
from aistack.transaction.transaction_manifest import TransactionManifest


def test_manifest_builder_returns_typed_manifest():
    tx = Transaction(
        transaction_id="KT-000004",
        definition_id="code.patch",
        payload=Path("payload.zip"),
    )

    manifest = ManifestBuilder().build(tx)

    assert isinstance(manifest, TransactionManifest)
    assert manifest.transaction_id == "KT-000004"
    assert manifest.definition_id == "code.patch"
    assert manifest.payload == "payload.zip"


def test_manifest_builder_exports_dictionary():
    tx = Transaction(
        transaction_id="KT-000004",
        definition_id="code.patch",
        payload=Path("payload.zip"),
    )

    manifest = ManifestBuilder().as_dict(tx)

    assert manifest == {
        "transaction_id": "KT-000004",
        "definition_id": "code.patch",
        "payload": "payload.zip",
    }
