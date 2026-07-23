from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import Request, Task
from aistack.kernel.registries.task_registry import TaskRegistry


@dataclass(frozen=True, slots=True)
class TaskResolver:
    """
    Resolve executable Tasks from execution Requests.

    Resolution is independent from Runtime orchestration.
    """

    tasks: TaskRegistry

    def resolve(self, request: Request) -> Task:
        return self.tasks.get(request.task_id)
