from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import Request, Task
from aistack.kernel.contracts import TaskSource


@dataclass(frozen=True, slots=True)
class TaskResolver:
    """
    Resolve executable Tasks from execution Requests.

    Resolution is independent from Runtime orchestration.
    """

    tasks: TaskSource

    def resolve(self, request: Request) -> Task:
        return self.tasks.get(request.task_id)
