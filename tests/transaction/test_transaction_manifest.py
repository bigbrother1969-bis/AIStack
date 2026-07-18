from dataclasses import FrozenInstanceError

import pytest

from aistack.transaction.transaction_manifest import TransactionManifest


def test_transaction_manifest_is_immutable():
    manifest = TransactionManifest(
        transaction_id="KT-000004",
        definition_id="code.patch",
        payload="payload.zip",
    )

    with pytest.raises(FrozenInstanceError):
        manifest.payload = "other.zip"
