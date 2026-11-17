from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import (
    Observation,
    RuntimeExecutionContext,
)
from aistack.kernel.resolution import (
    ResolutionContext,
    TaskResolver,
)
from aistack.kernel.tracing import (
    ExecutionPhase,
    ExecutionTrace,
    ExecutionTraceEvent,
    ExecutionTraceEventType,
)


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
        context: RuntimeExecutionContext,
    ) -> ExecutionTrace:

        events: list[ExecutionTraceEvent] = []

        events.append(
            ExecutionTraceEvent(
                phase=ExecutionPhase.REQUEST,
                event_type=ExecutionTraceEventType.REQUEST_RECEIVED,
                component="KernelRuntime",
                message="Runtime received request",
            )
        )

        resolution_context = ResolutionContext(
            request=context.request,
        )

        events.append(
            ExecutionTraceEvent(
                phase=ExecutionPhase.RESOLUTION,
                event_type=ExecutionTraceEventType.RESOLUTION_STARTED,
                component="TaskResolver",
                message="Task resolution started",
            )
        )

        resolution = self.resolver.resolve(
            resolution_context,
        )

        events.append(
            ExecutionTraceEvent(
                phase=ExecutionPhase.RESOLUTION,
                event_type=ExecutionTraceEventType.RESOLUTION_COMPLETED,
                component="TaskResolver",
                message="Task resolved",
            )
        )

        observation: Observation = resolution.task.execute(
            context.request,
        )

        events.append(
            ExecutionTraceEvent(
                phase=ExecutionPhase.EXECUTION,
                event_type=ExecutionTraceEventType.TASK_EXECUTED,
                component=resolution.task.task_id,
                message="Task executed",
            )
        )

        events.append(
            ExecutionTraceEvent(
                phase=ExecutionPhase.OBSERVATION,
                event_type=ExecutionTraceEventType.OBSERVATION_PRODUCED,
                component=resolution.task.task_id,
                message="Observation produced",
            )
        )

        return ExecutionTrace(
            request=context.request,
            resolution=resolution,
            observation=observation,
            events=tuple(events),
        )
