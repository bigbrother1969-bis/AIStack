from __future__ import annotations

from typing import Protocol

from aistack.kernel.runtime.observation import Observation
from aistack.kernel.runtime.request import Request


class Task(Protocol):
    """
    Runtime component responsible for executing one governed request.

    A Task may later resolve and execute Providers. The Runtime only knows
    the Task contract and never reaches directly into lower execution layers.
    """

    task_id: str
    task_name: str

    def execute(self, request: Request) -> Observation:
        ...
