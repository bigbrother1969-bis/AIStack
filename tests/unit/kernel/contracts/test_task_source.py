from __future__ import annotations

from aistack.kernel.contracts import TaskSource
from aistack.kernel.registries.task_registry import TaskRegistry

from tests.unit.kernel.contracts.conformance import (
    assert_implements,
)


def test_task_registry_implements_task_source() -> None:
    """
    What the previous version of this test did:

        assert isinstance(
            registry,
            TaskSource.__protocol_attrs__.__class__,
        ) is False

    `__protocol_attrs__` is a set, `.__class__` is `set`, and a
    `TaskRegistry` is not a `set`. The assertion held for a
    reason unrelated to TaskSource, TaskRegistry or the contract
    between them, and it required Python 3.12 to hold at all,
    since `__protocol_attrs__` is a CPython internal introduced
    there. On 3.11 the test did not fail — it errored.

    A conformance test asks one question: does the thing that is
    supposed to satisfy this contract actually satisfy it.
    """

    assert_implements(TaskSource, TaskRegistry)
