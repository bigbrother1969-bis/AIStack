from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from aistack.core.execution.execution_context import ExecutionContext


def test_execution_context_creation():

    context = ExecutionContext(
        execution_id="exec-001",
        execution_name="Docker Runtime Pipeline",
        started_at=datetime.now(),
        scenario="scenario-25",
        tags={"env": "test"},
        metadata={"version": "1"},
    )

    assert context.execution_id == "exec-001"
    assert context.execution_name == "Docker Runtime Pipeline"
    assert context.scenario == "scenario-25"

    assert context.tags["env"] == "test"
    assert context.metadata["version"] == "1"


def test_execution_context_is_immutable():

    context = ExecutionContext(
        execution_id="exec",
        execution_name="Pipeline",
        started_at=datetime.now(),
    )

    with pytest.raises(FrozenInstanceError):
        context.execution_name = "modified"
