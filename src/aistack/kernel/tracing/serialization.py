from __future__ import annotations

from typing import Any

from aistack.kernel.execution import Observation
from aistack.kernel.time import Provenance, VersionId
from aistack.kernel.tracing.trace import ExecutionTrace


def serialize_execution_trace(
    trace: ExecutionTrace,
    *,
    version: VersionId,
    provenance: Provenance,
) -> dict[str, Any]:
    """
    An `ExecutionTrace` as a JSON-safe `dict`, the shape
    `FileTraceRepository` persists.

    The live `Task` in `resolution.task` is not data; only its
    `task_id`/`task_name`, the resolver and the reason are written.
    There is no timestamp: the history filename states the instant.
    `version` and `provenance` are supplied by the caller, keeping this
    a pure mapping.
    """

    return {
        "version": {
            "subject": version.subject,
            "sequence": version.sequence,
        },
        "provenance": {
            "origin": provenance.origin,
            "causality": provenance.causality,
        },
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
