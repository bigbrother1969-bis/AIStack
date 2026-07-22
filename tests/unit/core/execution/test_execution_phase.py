from dataclasses import FrozenInstanceError

import pytest

from aistack.core.execution.execution_phase import ExecutionPhase


def test_execution_phase_creation():

    phase = ExecutionPhase(
        id="transport",
        name="Transport",
        description="Copies files",
        order=2,
    )

    assert phase.id == "transport"
    assert phase.name == "Transport"
    assert phase.description == "Copies files"
    assert phase.order == 2


def test_execution_phase_is_immutable():

    phase = ExecutionPhase(
        id="prepare",
        name="Prepare",
    )

    with pytest.raises(FrozenInstanceError):
        phase.name = "Modified"
