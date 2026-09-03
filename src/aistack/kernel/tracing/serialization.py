from __future__ import annotations

from typing import Any

from aistack.kernel.execution import Observation
from aistack.kernel.tracing.trace import ExecutionTrace


def serialize_execution_trace(trace: ExecutionTrace) -> dict[str, Any]:
    """
    An `ExecutionTrace` as a JSON-safe `dict` — the shape
    `FileTraceRepository` persists.

    **`resolution.task` is not serialized — it cannot be.**
    `ResolutionResult.task` holds the live `Task` object that
    executed, an executable, not data (`kernel/resolution/result.py`).
    What is written instead is exactly what the trace itself needs to
    explain a resolution: the task's own `task_id`/`task_name`,
    `resolver`, `reason` — everything `ADR-0008`'s roadmap asks a
    Runtime Operation History entry to carry ("applied rules")
    except the executable itself, which a JSON file was never going
    to hold.

    **No `timestamp` field is written here, and none is missing.**
    Neither `ExecutionTrace` nor `ExecutionTraceEvent` carries one —
    the roadmap's own required field
    (`docs/99-meta/roadmap/AIStack-Medium-Term-Development-Roadmap.md`
    § *Runtime Operation History*) is instead the instant already
    encoded in the history filename `write_artifact_with_history`
    gives this content, the same convention every other historicised
    artifact already relies on (`aistack.history.query`). Adding a
    second, independent timestamp inside the content would be one
    more fact that can drift from the one the filename already
    states.
    """

    return {
        "request": {
            "request_id": trace.request.request_id,
            "task_id": trace.request.task_id,
            "payload": dict(trace.request.payload),
        },
        "resolution": {
            "task_id": trace.resolution.task.task_id,
            "task_name": trace.resolution.task.task_name,
            "resolver": trace.resolution.resolver,
            "reason": trace.resolution.reason,
        },
        "observation": _serialize_observation(trace.observation),
        "events": [
            {
                "phase": event.phase.value,
                "event_type": event.event_type.value,
                "component": event.component,
                "message": event.message,
            }
            for event in trace.events
        ],
    }


def _serialize_observation(observation: Observation) -> dict[str, Any]:
    return {
        "context": {
            "request_id": observation.context.request_id,
            "component_type": observation.context.component_type,
            "component_id": observation.context.component_id,
            "operation": observation.context.operation,
        },
        "data": dict(observation.data),
        "children": [
            _serialize_observation(child) for child in observation.children
        ],
    }
