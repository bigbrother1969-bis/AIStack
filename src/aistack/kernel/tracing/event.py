from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ExecutionTraceEventType(str, Enum):
    REQUEST_RECEIVED = "request_received"
    RESOLUTION_STARTED = "resolution_started"
    RESOLUTION_COMPLETED = "resolution_completed"
    TASK_EXECUTED = "task_executed"
    OBSERVATION_PRODUCED = "observation_produced"


@dataclass(frozen=True, slots=True)
class ExecutionTraceEvent:
    """
    Immutable event emitted during Runtime execution.
    """

    event_type: ExecutionTraceEventType
    message: str
