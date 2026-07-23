from aistack.kernel.contracts import TaskSource
from aistack.kernel.registries.task_registry import TaskRegistry


def test_task_registry_implements_task_source_contract() -> None:
    registry = TaskRegistry()

    assert isinstance(registry, TaskSource.__protocol_attrs__.__class__) is False
