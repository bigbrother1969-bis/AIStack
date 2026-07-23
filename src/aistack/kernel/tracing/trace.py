from __future__ import annotations

from dataclasses import dataclass, field

from aistack.kernel.execution import Observation, Request
from aistack.kernel.resolution import ResolutionResult
from aistack.kernel.tracing.event import ExecutionTraceEvent


@dataclass(frozen=True, slots=True)
class ExecutionTrace:
    """
    Immutable execution trace.

    An ExecutionTrace is the explainable artifact produced by Runtime.

    It keeps:
    - the original request;
    - the resolution decision;
    - the resulting observation;
    - the chronological execution events.
    """

    request: Request
    resolution: ResolutionResult
    observation: Observation
    events: tuple[ExecutionTraceEvent, ...] = field(
        default_factory=tuple
    )

    def append(
        self,
        event: ExecutionTraceEvent,
    ) -> "ExecutionTrace":
        return ExecutionTrace(
            request=self.request,
            resolution=self.resolution,
            observation=self.observation,
            events=self.events + (event,),
        )
