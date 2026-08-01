from __future__ import annotations

from aistack.kernel.contracts.registry import Registry


def test_registry_contract_is_importable() -> None:
    assert Registry is not None


def test_registry_exposes_read_only_operations() -> None:
    assert callable(Registry.get)
    assert callable(Registry.contains)
    assert callable(Registry.items)
