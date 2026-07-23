from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class Request:
    """
    Immutable request submitted to the AIStack Runtime.

    A Request expresses what must be executed without resolving or
    constructing the Task responsible for its execution.
    """

    request_id: str
    task_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
