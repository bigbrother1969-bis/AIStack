from dataclasses import FrozenInstanceError

import pytest

from aistack.kernel.execution import Request


def test_request_preserves_runtime_intent() -> None:
    request = Request(
        request_id="request-001",
        task_id="task.discovery",
        payload={"source": "docker"},
    )

    assert request.request_id == "request-001"
    assert request.task_id == "task.discovery"
    assert request.payload == {"source": "docker"}


def test_request_payload_defaults_to_empty_mapping() -> None:
    request = Request(
        request_id="request-001",
        task_id="task.discovery",
    )

    assert request.payload == {}


def test_request_is_immutable() -> None:
    request = Request(
        request_id="request-001",
        task_id="task.discovery",
    )

    with pytest.raises(FrozenInstanceError):
        request.task_id = "task.other"
