from __future__ import annotations

from typing import Protocol

from aistack.kernel.execution import Task


class TaskSource(Protocol):
    """
    Contract used by Resolution Layer to retrieve executable Tasks.

    Resolution depends on a capability, not on a storage implementation.
    """

    def get(self, task_id: str) -> Task:
        ...
