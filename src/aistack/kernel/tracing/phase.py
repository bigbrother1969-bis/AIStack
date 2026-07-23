from __future__ import annotations

from enum import Enum


class ExecutionPhase(str, Enum):
    """
    Major phases of Runtime execution.
    """

    REQUEST = "request"
    RESOLUTION = "resolution"
    EXECUTION = "execution"
    OBSERVATION = "observation"
