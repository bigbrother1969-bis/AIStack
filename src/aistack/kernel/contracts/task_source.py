from __future__ import annotations

from typing import Protocol

from aistack.kernel.execution import Task


class TaskSource(Protocol):
    """
    Contract used by Resolution Layer to retrieve executable Tasks.

    Resolution depends on a capability, not on a storage implementation.

    `task_id` is positional-only, and that is a statement rather
    than a style: the contract requires a lookup by identifier
    and does not require implementations to agree on what to
    call it. Declared as a keyword parameter, it silently made
    `source.get(task_id=...)` part of the contract, which the
    implementation — `Registry.get(self, identifier)` — does not
    honour.
    """

    def get(self, task_id: str, /) -> Task:
        ...
