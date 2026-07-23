from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class ObservationContext:
    """
    Traceability context attached to one execution Observation.
    """

    request_id: str
    component_type: str
    component_id: str
    operation: str


@dataclass(frozen=True, slots=True)
class Observation:
    """
    Result produced by one Runtime execution component.

    Observations are recursive. An atomic Observation has no children.
    Composite Observations preserve the Observations returned by their
    directly executed children.
    """

    context: ObservationContext
    data: Mapping[str, Any] = field(default_factory=dict)
    children: tuple["Observation", ...] = field(default_factory=tuple)

    @property
    def is_atomic(self) -> bool:
        return not self.children
