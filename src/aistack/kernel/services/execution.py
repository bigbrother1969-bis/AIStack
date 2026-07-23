from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.tracing.repository import TraceRepository


@dataclass(frozen=True, slots=True)
class ExecutionServices:
    """
    Services related to Runtime execution lifecycle.

    ExecutionServices owns execution-related
    persistence and lifecycle services.
    """

    trace_repository: TraceRepository
