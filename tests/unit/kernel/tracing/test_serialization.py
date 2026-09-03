"""
`serialize_execution_trace` — the JSON-safe shape
`FileTraceRepository` persists (Runtime Operation History,
2026-09-03).
"""

from __future__ import annotations

from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.kernel.resolution import ResolutionResult
from aistack.kernel.tracing import (
    ExecutionPhase,
    ExecutionTrace,
    ExecutionTraceEvent,
    ExecutionTraceEventType,
    serialize_execution_trace,
)


class FakeTask:
    task_id = "task.fake"
    task_name = "Fake Task"

    def execute(self, request: Request) -> Observation:
        raise NotImplementedError


def _trace() -> ExecutionTrace:
    request = Request(
        request_id="request-001",
        task_id="task.fake",
        payload={"output_path": "reports/generated/x.json"},
    )

    resolution = ResolutionResult(
        task=FakeTask(),
        resolver="TaskResolver",
        reason="Task resolved from identifier 'task.fake'",
    )

    observation = Observation(
        context=ObservationContext(
            request_id="request-001",
            component_type="task",
            component_id="task.fake",
            operation="execute",
        ),
        data={"output_path": "reports/generated/x.json"},
        children=(
            Observation(
                context=ObservationContext(
                    request_id="request-001",
                    component_type="child",
                    component_id="task.fake.child",
                    operation="execute",
                ),
                data={"n": 1},
            ),
        ),
    )

    events = (
        ExecutionTraceEvent(
            phase=ExecutionPhase.REQUEST,
            event_type=ExecutionTraceEventType.REQUEST_RECEIVED,
            component="KernelRuntime",
            message="Runtime received request",
        ),
    )

    return ExecutionTrace(
        request=request,
        resolution=resolution,
        observation=observation,
        events=events,
    )


def test_it_serializes_the_request():
    serialized = serialize_execution_trace(_trace())

    assert serialized["request"] == {
        "request_id": "request-001",
        "task_id": "task.fake",
        "payload": {"output_path": "reports/generated/x.json"},
    }


def test_it_serializes_the_resolution_without_the_live_task_object():
    """
    `resolution.task` is an executable, not data — it cannot survive
    a round trip through JSON, so it is never attempted. What is
    written is exactly what identifies and explains the resolution.
    """

    serialized = serialize_execution_trace(_trace())

    assert serialized["resolution"] == {
        "task_id": "task.fake",
        "task_name": "Fake Task",
        "resolver": "TaskResolver",
        "reason": "Task resolved from identifier 'task.fake'",
    }
    assert "task" not in serialized["resolution"]


def test_it_serializes_the_observation_and_its_children_recursively():
    serialized = serialize_execution_trace(_trace())

    assert serialized["observation"]["context"]["component_id"] == "task.fake"
    assert serialized["observation"]["data"] == {
        "output_path": "reports/generated/x.json"
    }
    assert len(serialized["observation"]["children"]) == 1
    assert serialized["observation"]["children"][0]["data"] == {"n": 1}


def test_it_serializes_events_with_plain_string_enum_values():
    serialized = serialize_execution_trace(_trace())

    assert serialized["events"] == [
        {
            "phase": "request",
            "event_type": "request_received",
            "component": "KernelRuntime",
            "message": "Runtime received request",
        }
    ]


def test_the_result_is_actually_json_serializable():
    import json

    json.dumps(serialize_execution_trace(_trace()))
