from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.registries.task_registry import TaskRegistry
from aistack.kernel.runtime.request import Request
from aistack.kernel.execution.task import Task


@dataclass(frozen=True, slots=True)
class RuntimeResolver:
    """
    Resolve the immediate execution child of the Runtime.

    The Runtime resolves Tasks only. Resolution of Providers belongs to
    Tasks and will be introduced when the Provider execution protocol is
    implemented.
    """

    tasks: TaskRegistry

    def resolve_task(self, request: Request) -> Task:
        return self.tasks.get(request.task_id)
