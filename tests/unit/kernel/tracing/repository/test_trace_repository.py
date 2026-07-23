from __future__ import annotations

from aistack.kernel.tracing import (
    InMemoryTraceRepository,
)


def test_trace_repository_stores_execution_trace() -> None:
    repository = InMemoryTraceRepository()

    trace = object()

    repository.save(trace)

    assert repository.get_all() == (
        trace,
    )
