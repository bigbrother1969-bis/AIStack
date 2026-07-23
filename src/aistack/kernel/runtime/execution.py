from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import Observation, Request
from aistack.kernel.resolution import TaskResolver


@dataclass(frozen=True, slots=True)
class RuntimeExecutor:
    """
    Execute Runtime Requests through resolved Tasks.

    Execution and Resolution remain separate responsibilities.
    """

    resolver: TaskResolver

    def execute(self, request: Request) -> Observation:
        task = self.resolver.resolve(request)
        return task.execute(request)
