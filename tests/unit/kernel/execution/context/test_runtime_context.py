from __future__ import annotations

from aistack.kernel.execution import (
    Request,
    RuntimeExecutionContext,
)


def test_runtime_execution_context_preserves_request() -> None:
    request = Request(
        request_id="request-001",
        task_id="task.test",
    )

    context = RuntimeExecutionContext(
        request=request,
    )

    assert context.request is request
    assert context.trace is None
    assert context.metadata == {}
