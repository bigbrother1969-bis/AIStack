from aistack.kernel.execution import (
    Observation,
    ObservationContext,
    Request,
    Task,
)
from aistack.kernel.resolution import ResolutionResult
from aistack.kernel.tracing import (
    ExecutionPhase,
    ExecutionTrace,
    ExecutionTraceEvent,
    ExecutionTraceEventType,
)


class DummyTask(Task):
    task_id = "task.test"

    def execute(self, request: Request) -> Observation:
        raise NotImplementedError


def test_execution_trace_preserves_execution_chain() -> None:
    request = Request(
        request_id="request-001",
        task_id="task.test",
    )

    task = DummyTask()

    resolution = ResolutionResult(
        task=task,
        resolver="TaskResolver",
        reason="selected task",
    )

    observation = Observation(
        context=ObservationContext(
            request_id="request-001",
            component_type="task",
            component_id="task.test",
            operation="execute",
        ),
        data={"ok": True},
    )


    trace = ExecutionTrace(
        request=request,
        resolution=resolution,
        observation=observation,
        events=(
            ExecutionTraceEvent(
                phase=ExecutionPhase.REQUEST,
                event_type=ExecutionTraceEventType.REQUEST_RECEIVED,
                component="KernelRuntime",
                message="Runtime received request",
            ),
        ),
    )


    assert trace.request is request
    assert trace.resolution is resolution
    assert trace.observation is observation
    assert trace.events[0].phase is ExecutionPhase.REQUEST
