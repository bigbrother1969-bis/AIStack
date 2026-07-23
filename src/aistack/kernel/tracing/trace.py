from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import Observation, Request
from aistack.kernel.resolution import ResolutionResult


@dataclass(frozen=True, slots=True)
class ExecutionTrace:
    """
    Complete explanation of a Runtime execution.

    It preserves:
    - original request
    - resolution decision
    - produced observation
    """

    request: Request
    resolution: ResolutionResult
    observation: Observation
