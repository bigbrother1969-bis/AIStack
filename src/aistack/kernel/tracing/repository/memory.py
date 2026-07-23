from __future__ import annotations

from dataclasses import dataclass, field

from aistack.kernel.tracing import ExecutionTrace
from aistack.kernel.tracing.repository.contract import TraceRepository


@dataclass
class InMemoryTraceRepository(TraceRepository):
    """
    In-memory trace repository.

    Used for runtime execution and tests.
    """

    traces: list[ExecutionTrace] = field(
        default_factory=list
    )

    def save(
        self,
        trace: ExecutionTrace,
    ) -> None:
        self.traces.append(trace)

    def get_all(
        self,
    ) -> tuple[ExecutionTrace, ...]:
        return tuple(self.traces)
