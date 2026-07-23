from __future__ import annotations

from typing import Protocol

from aistack.kernel.execution.observation import Observation
from aistack.kernel.execution.request import Request


class Task(Protocol):
    """
    Execution contract.

    A Task executes one Request and produces one Observation.
    """

    task_id: str
    task_name: str

    def execute(self, request: Request) -> Observation:
        ...
