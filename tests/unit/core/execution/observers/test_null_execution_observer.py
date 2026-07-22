from datetime import datetime, timezone

from aistack.core.execution.execution_context import ExecutionContext
from aistack.core.execution.execution_event import ExecutionEvent
from aistack.core.execution.execution_event_type import ExecutionEventType
from aistack.core.execution.observers.null_execution_observer import (
    NullExecutionObserver,
)


def test_null_execution_observer_accepts_event_without_side_effect():
    timestamp = datetime.now(timezone.utc)

    context = ExecutionContext(
        execution_id="exec-null",
        execution_name="Pipeline",
        started_at=timestamp,
    )

    event = ExecutionEvent(
        type=ExecutionEventType.EXECUTION_STARTED,
        timestamp=timestamp,
        context=context,
    )

    observer = NullExecutionObserver()

    result = observer.on_event(event)

    assert result is None
