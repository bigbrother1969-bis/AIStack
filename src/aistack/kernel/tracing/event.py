from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from aistack.kernel.tracing.phase import ExecutionPhase


class ExecutionTraceEventType(str, Enum):
    REQUEST_RECEIVED = "request_received"
    RESOLUTION_STARTED = "resolution_started"
    RESOLUTION_COMPLETED = "resolution_completed"
    TASK_EXECUTED = "task_executed"
    OBSERVATION_PRODUCED = "observation_produced"


@dataclass(frozen=True, slots=True)
class ExecutionTraceEvent:
    """
    Immutable execution event.

    Each event explains one step of Runtime execution.
    """

    phase: ExecutionPhase
    event_type: ExecutionTraceEventType
    component: str
    message: str
