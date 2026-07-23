from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.runtime.observation import Observation
from aistack.kernel.runtime.request import Request
from aistack.kernel.runtime.resolution import RuntimeResolver


@dataclass(frozen=True, slots=True)
class RuntimeExecutor:
    """
    Execute Runtime Requests through resolved Tasks.

    Execution and Resolution remain separate responsibilities.
    """

    resolver: RuntimeResolver

    def execute(self, request: Request) -> Observation:
        task = self.resolver.resolve_task(request)
        return task.execute(request)
