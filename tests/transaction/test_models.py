from pathlib import Path

from aistack.transaction.models import Transaction


def test_transaction_is_immutable():
    tx = Transaction(
        transaction_id="KT-000001",
        definition_id="code.patch",
        payload=Path("patch.diff"),
    )

    assert tx.transaction_id == "KT-000001"
    assert tx.definition_id == "code.patch"
    assert tx.payload.name == "patch.diff"
