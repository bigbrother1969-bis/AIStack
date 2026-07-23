from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.contracts import TaskSource
from aistack.kernel.execution import Task
from aistack.kernel.resolution.context import ResolutionContext


@dataclass(frozen=True, slots=True)
class TaskResolver:
    """
    Resolve executable Tasks from Resolution Context.

    Resolution depends on contracts, not implementations.
    """

    tasks: TaskSource

    def resolve(self, context: ResolutionContext) -> Task:
        return self.tasks.get(context.request.task_id)
