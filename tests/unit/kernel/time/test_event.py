from dataclasses import FrozenInstanceError

import pytest

from aistack.kernel.time import TemporalEvent


def test_temporal_event_carries_subject_type_and_message() -> None:
    event = TemporalEvent(
        subject="docker.discover",
        event_type="cpu.decision.applied",
        message="jellyfin boosted to 4 CPUs",
    )

    assert event.subject == "docker.discover"
    assert event.event_type == "cpu.decision.applied"
    assert event.message == "jellyfin boosted to 4 CPUs"


def test_temporal_event_is_immutable() -> None:
    event = TemporalEvent(
        subject="s",
        event_type="t",
        message="m",
    )

    with pytest.raises(FrozenInstanceError):
        event.message = "changed"


def test_temporal_event_event_type_is_a_free_string_not_a_shared_enum() -> None:
    """
    Two unrelated streams naming their own event types, neither
    drawn from a shared enum — the point of this contract over a
    single central `ExecutionTraceEventType`-style enum every stream
    would otherwise have to extend.
    """

    runtime_event = TemporalEvent(
        subject="KernelRuntime",
        event_type="request_received",
        message="Runtime received request",
    )
    decision_event = TemporalEvent(
        subject="resource_priority_monitor",
        event_type="cpu.decision.applied",
        message="jellyfin boosted",
    )

    assert runtime_event.event_type != decision_event.event_type
