from __future__ import annotations

from aistack.kernel.contracts.mutable_registry import (
    MutableRegistry,
)


def test_mutable_registry_contract_is_importable() -> None:
    assert MutableRegistry is not None


def test_mutable_registry_exposes_mutation_operations() -> None:
    assert callable(MutableRegistry.register)
    assert callable(MutableRegistry.freeze)
