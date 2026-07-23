from __future__ import annotations

from aistack.kernel.registry import Registry
from aistack.kernel.execution.task import Task


class TaskRegistry(Registry[Task]):
    """Registry used by the Runtime to resolve Tasks."""

    pass
