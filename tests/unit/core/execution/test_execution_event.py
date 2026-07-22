from dataclasses import FrozenInstanceError
from datetime import datetime, timezone

import pytest

from aistack.core.execution.execution_context import ExecutionContext
from aistack.core.execution.execution_event import ExecutionEvent
from aistack.core.execution.execution_event_type import ExecutionEventType
from aistack.core.execution.execution_phase import ExecutionPhase


def test_execution_event_creation():
    started_at = datetime.now(timezone.utc)

    context = ExecutionContext(
        execution_id="exec-001",
        execution_name="Docker Runtime Pipeline",
        started_at=started_at,
        scenario="scenario-25",
    )

    phase = ExecutionPhase(
        id="transport",
        name="Transport",
        description="Transfers the qualification artifact",
        order=3,
    )

    event = ExecutionEvent(
        type=ExecutionEventType.PHASE_STARTED,
        timestamp=started_at,
        context=context,
        phase=phase,
        payload={
            "source": "/tmp/source.bin",
            "destination": "/tmp/destination.bin",
        },
        metadata={
            "host": "GIGABYTE",
        },
    )

    assert event.type is ExecutionEventType.PHASE_STARTED
    assert event.timestamp == started_at
    assert event.context is context
    assert event.phase is phase
    assert event.payload["source"] == "/tmp/source.bin"
    assert event.metadata["host"] == "GIGABYTE"


def test_execution_event_defaults():
    timestamp = datetime.now(timezone.utc)

    context = ExecutionContext(
        execution_id="exec-002",
        execution_name="Pipeline",
        started_at=timestamp,
    )

    event = ExecutionEvent(
        type=ExecutionEventType.EXECUTION_STARTED,
        timestamp=timestamp,
        context=context,
    )

    assert event.phase is None
    assert event.payload == {}
    assert event.metadata == {}


def test_execution_event_is_immutable():
    timestamp = datetime.now(timezone.utc)

    context = ExecutionContext(
        execution_id="exec-003",
        execution_name="Pipeline",
        started_at=timestamp,
    )

    event = ExecutionEvent(
        type=ExecutionEventType.EXECUTION_STARTED,
        timestamp=timestamp,
        context=context,
    )

    with pytest.raises(FrozenInstanceError):
        event.type = ExecutionEventType.ERROR
