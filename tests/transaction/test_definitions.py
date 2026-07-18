from aistack.transaction.definitions import TransactionDefinition


def test_definition_defaults():
    d = TransactionDefinition("code.patch")
    assert d.definition_id == "code.patch"
    assert d.version == "1.0"
