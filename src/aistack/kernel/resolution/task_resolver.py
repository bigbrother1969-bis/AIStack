from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.contracts import TaskSource
from aistack.kernel.resolution.result import ResolutionResult
from aistack.kernel.resolution.context import ResolutionContext


@dataclass(frozen=True, slots=True)
class TaskResolver:
    """
    Resolve executable Tasks from Resolution Context.

    Resolution depends on contracts, not implementations.
    """

    tasks: TaskSource

    def resolve(self, context: ResolutionContext) -> ResolutionResult:
        task = self.tasks.get(context.request.task_id)

        return ResolutionResult(
            task=task,
            resolver=self.__class__.__name__,
            reason=f"Task resolved from identifier '{context.request.task_id}'",
        )
