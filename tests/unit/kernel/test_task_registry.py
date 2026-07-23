from aistack.kernel.execution import Observation, Request
from aistack.kernel.registries.task_registry import TaskRegistry


class DummyTask:
    task_id = "dummy.task"
    task_name = "Dummy Task"

    def execute(self, request: Request) -> Observation:
        raise NotImplementedError


def test_task_registry_register_and_resolve() -> None:
    registry = TaskRegistry()
    task = DummyTask()

    registry.register(task.task_id, task)

    resolved = registry.get(task.task_id)

    assert resolved is task


def test_task_registry_contains_task() -> None:
    registry = TaskRegistry()
    task = DummyTask()

    registry.register(task.task_id, task)

    assert task.task_id in registry
