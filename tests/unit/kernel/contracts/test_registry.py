from __future__ import annotations

from aistack.kernel.contracts.registry import Registry
from aistack.kernel.registry import Registry as KernelRegistry
from aistack.kernel.registries.task_registry import TaskRegistry

from tests.unit.kernel.contracts.conformance import (
    assert_implements,
    protocol_members,
)


def test_the_kernel_registry_implements_the_contract() -> None:
    """
    What this test replaced:

        assert callable(Registry.get)
        assert callable(Registry.contains)
        assert callable(Registry.items)

    Three assertions that a Protocol declares what it declares.
    They passed every day while `contains` and `items` existed
    nowhere but in that file.
    """

    assert_implements(Registry, KernelRegistry)


def test_every_kernel_registry_implements_the_contract() -> None:

    assert_implements(Registry, TaskRegistry)


def test_membership_is_part_of_the_contract() -> None:
    """
    `__contains__` is a dunder, and a conformance check that
    filtered leading underscores would silently drop it. It is
    named here so that filtering it out again fails a test
    rather than passing one.
    """

    assert "__contains__" in protocol_members(Registry)
