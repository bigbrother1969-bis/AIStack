from __future__ import annotations

import pytest

from aistack.kernel.execution import (
    Observation,
    ObservationContext,
)
from aistack.kernel.runtime import (
    KernelRuntime,
    Request,
)
from aistack.kernel.tracing import (
    ExecutionTraceEventType,
)

class RecordingTask:
    task_id = "task.recording"
    task_name = "Recording Task"

    def __init__(self) -> None:
        self.received_request = None

    def execute(self, request: Request) -> Observation:
        self.received_request = request

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={"executed": True},
        )


def test_runtime_resolves_and_executes_registered_task() -> None:
    runtime = KernelRuntime.boot()
    task = RecordingTask()

    runtime.kernel.registries.tasks.register(
        task.task_id,
        task,
    )

    request = Request(
        request_id="request-001",
        task_id=task.task_id,
    )

    trace = runtime.execute(request)

    assert task.received_request is request

    assert trace.request is request
    assert trace.resolution.task is task

    assert trace.observation.context.request_id == request.request_id
    assert trace.observation.context.component_id == task.task_id
    assert trace.observation.data == {"executed": True}

    assert len(trace.events) == 5

    assert trace.events[0].event_type is (
        ExecutionTraceEventType.REQUEST_RECEIVED
    )

    assert trace.events[1].event_type is (
        ExecutionTraceEventType.RESOLUTION_STARTED
    )

    assert trace.events[2].event_type is (
        ExecutionTraceEventType.RESOLUTION_COMPLETED
    )

    assert trace.events[3].event_type is (
        ExecutionTraceEventType.TASK_EXECUTED
    )

    assert trace.events[4].event_type is (
        ExecutionTraceEventType.OBSERVATION_PRODUCED
    )

def test_runtime_does_not_resolve_unknown_task() -> None:
    runtime = KernelRuntime.boot()

    request = Request(
        request_id="request-001",
        task_id="task.unknown",
    )

    with pytest.raises(KeyError):
        runtime.execute(request)
