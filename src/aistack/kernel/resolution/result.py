from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.execution import Task


@dataclass(frozen=True, slots=True)
class ResolutionResult:
    """
    Result produced by the Resolution Layer.

    The result keeps the selected executable element and
    the information required to explain the resolution.
    """

    task: Task
    resolver: str
    reason: str
