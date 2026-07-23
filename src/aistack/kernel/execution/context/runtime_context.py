from __future__ import annotations

from dataclasses import dataclass, field

from aistack.kernel.execution import Request


@dataclass(frozen=True, slots=True)
class RuntimeExecutionContext:
    """
    Runtime execution context.

    Carries the immutable execution state during
    a Runtime operation.
    """

    request: Request
    trace: object | None = None
    metadata: dict[str, str] = field(
        default_factory=dict
    )
