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


def test_runtime_does_not_resolve_unknown_task() -> None:
    runtime = KernelRuntime.boot()

    request = Request(
        request_id="request-001",
        task_id="task.unknown",
    )

    with pytest.raises(KeyError):
        runtime.execute(request)
