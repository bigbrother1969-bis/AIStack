from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from .execution_context import ExecutionContext
from .execution_event_type import ExecutionEventType
from .execution_phase import ExecutionPhase


@dataclass(frozen=True)
class ExecutionEvent:
    type: ExecutionEventType
    timestamp: datetime

    context: ExecutionContext

    phase: ExecutionPhase | None = None

    payload: Mapping[str, Any] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
