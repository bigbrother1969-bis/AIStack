from __future__ import annotations

from aistack.kernel.execution.task import Task
from aistack.kernel.registry import Registry


class TaskRegistry(Registry[Task]):
    """Registry used to resolve executable Tasks."""

    pass
