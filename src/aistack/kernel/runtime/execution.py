from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import Observation, Request
from aistack.kernel.resolution import (
    ResolutionContext,
    TaskResolver,
)
from aistack.kernel.tracing import ExecutionTrace


@dataclass(frozen=True, slots=True)
class RuntimeExecutor:
    """
    Execute Runtime Requests.

    Resolution, execution and produced knowledge
    are captured inside an ExecutionTrace.
    """

    resolver: TaskResolver

    def execute(
        self,
        request: Request,
    ) -> ExecutionTrace:

        context = ResolutionContext(
            request=request,
        )

        resolution = self.resolver.resolve(
            context,
        )

        observation = resolution.task.execute(
            request,
        )

        return ExecutionTrace(
            request=request,
            resolution=resolution,
            observation=observation,
        )
