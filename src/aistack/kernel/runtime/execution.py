from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import Observation, Request
from aistack.kernel.resolution import TaskResolver
from aistack.kernel.resolution import ResolutionContext

@dataclass(frozen=True, slots=True)
class RuntimeExecutor:
    """
    Execute Runtime Requests through resolved Tasks.

    Execution and Resolution remain separate responsibilities.
    """

    resolver: TaskResolver



    def execute(self, request: Request) -> Observation:
        context = ResolutionContext(request=request)

        resolution = self.resolver.resolve(context)

        return resolution.task.execute(request)
