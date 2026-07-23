from dataclasses import FrozenInstanceError

import pytest

from aistack.kernel.execution import Request


def test_request_creation() -> None:
    request = Request(
        request_id="request-001",
        task_id="task.discovery",
        payload={"provider": "docker"},
    )

    assert request.request_id == "request-001"
    assert request.task_id == "task.discovery"
    assert request.payload == {"provider": "docker"}


def test_request_default_payload() -> None:
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
        request.task_id = "another-task"
