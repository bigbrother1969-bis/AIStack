from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ObservationContext:
    """
    Traceability context attached to one execution observation.
    """

    request_id: str
    component_type: str
    component_id: str
    operation: str


@dataclass(frozen=True, slots=True)
class Observation:
    """
    Result produced by one execution component.

    Observations are recursive. An atomic Observation has no children.
    """

    context: ObservationContext
    data: Mapping[str, Any] = field(default_factory=dict)
    children: tuple["Observation", ...] = field(default_factory=tuple)

    @property
    def is_atomic(self) -> bool:
        return len(self.children) == 0
