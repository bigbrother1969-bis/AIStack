from datetime import datetime, timezone

import pytest

from aistack.core.execution.execution_context import ExecutionContext
from aistack.core.execution.execution_event import ExecutionEvent
from aistack.core.execution.execution_event_type import ExecutionEventType
from aistack.core.execution.observers.composite_execution_observer import (
    CompositeExecutionObserver,
)
from aistack.core.execution.observers.execution_observer import (
    ExecutionObserver,
)


class RecordingObserver(ExecutionObserver):
    def __init__(self, name: str, history: list[str]) -> None:
        self.name = name
        self.history = history
        self.events: list[ExecutionEvent] = []

    def on_event(self, event: ExecutionEvent) -> None:
        self.history.append(self.name)
        self.events.append(event)


class FailingObserver(ExecutionObserver):
    def on_event(self, event: ExecutionEvent) -> None:
        raise RuntimeError("observer failure")


def build_event() -> ExecutionEvent:
    timestamp = datetime.now(timezone.utc)

    context = ExecutionContext(
        execution_id="exec-composite",
        execution_name="Pipeline",
        started_at=timestamp,
    )

    return ExecutionEvent(
        type=ExecutionEventType.EXECUTION_STARTED,
        timestamp=timestamp,
        context=context,
    )


def test_composite_execution_observer_dispatches_event_to_all_observers():
    history: list[str] = []

    first = RecordingObserver("first", history)
    second = RecordingObserver("second", history)
    third = RecordingObserver("third", history)

    composite = CompositeExecutionObserver(
        observers=[first, second, third]
    )

    event = build_event()

    composite.on_event(event)

    assert first.events == [event]
    assert second.events == [event]
    assert third.events == [event]


def test_composite_execution_observer_preserves_registration_order():
    history: list[str] = []

    composite = CompositeExecutionObserver(
        observers=[
            RecordingObserver("first", history),
            RecordingObserver("second", history),
            RecordingObserver("third", history),
        ]
    )

    composite.on_event(build_event())

    assert history == [
        "first",
        "second",
        "third",
    ]


def test_composite_execution_observer_accepts_empty_collection():
    composite = CompositeExecutionObserver(observers=[])

    result = composite.on_event(build_event())

    assert result is None


def test_composite_execution_observer_propagates_observer_failure():
    history: list[str] = []

    first = RecordingObserver("first", history)
    failing = FailingObserver()
    third = RecordingObserver("third", history)

    composite = CompositeExecutionObserver(
        observers=[
            first,
            failing,
            third,
        ]
    )

    with pytest.raises(RuntimeError, match="observer failure"):
        composite.on_event(build_event())

    assert history == ["first"]
    assert third.events == []
