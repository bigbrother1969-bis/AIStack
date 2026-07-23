from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class Request:
    """
    Immutable execution request.

    A Request expresses what must be executed without describing how the
    execution is performed.
    """

    request_id: str
    task_id: str
    payload: Mapping[str, Any] = field(default_factory=dict)
