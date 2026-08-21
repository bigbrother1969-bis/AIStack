from __future__ import annotations

from aistack.kernel.contracts.mutable_registry import (
    MutableRegistry,
)
from aistack.kernel.contracts.registry import Registry
from aistack.kernel.registry import Registry as KernelRegistry

from tests.unit.kernel.contracts.conformance import (
    protocol_members,
)
from tests.unit.kernel.contracts.conformance import (
    assert_implements,
)


def test_the_kernel_registry_implements_the_mutable_contract() -> None:

    assert_implements(MutableRegistry, KernelRegistry)


def test_the_mutable_contract_extends_the_read_only_one() -> None:
    """
    Inheritance is the reason `protocol_members` walks the MRO.
    A `MutableRegistry` must satisfy everything a `Registry`
    requires; a check that only read the subclass namespace
    would have verified `register` and nothing else.
    """

    assert protocol_members(Registry) < protocol_members(
        MutableRegistry
    )


def test_freeze_is_no_longer_claimed() -> None:
    """
    `freeze() -> Registry[T]` was declared by this contract and
    implemented by nothing, from the day it was written until
    2026-08-21. This test states its absence so that reinstating
    it means writing it, not declaring it.
    """

    assert "freeze" not in protocol_members(MutableRegistry)
