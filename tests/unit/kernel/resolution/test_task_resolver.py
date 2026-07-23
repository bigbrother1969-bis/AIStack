from aistack.kernel.execution import Observation, Request
from aistack.kernel.resolution import ResolutionContext, TaskResolver
from aistack.kernel.registries.task_registry import TaskRegistry


class DummyTask:
    task_id = "dummy.task"
    task_name = "Dummy Task"

    def execute(self, request: Request) -> Observation:
        raise NotImplementedError


def test_task_resolver_resolves_registered_task() -> None:
    registry = TaskRegistry()
    task = DummyTask()

    registry.register(task.task_id, task)

    resolver = TaskResolver(tasks=registry)

    resolved = resolver.resolve(
        ResolutionContext(
            request=Request(
                request_id="request-001",
                task_id=task.task_id,
            )
        )
    )

    assert resolved is task
