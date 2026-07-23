from aistack.kernel.execution import Request
from aistack.kernel.resolution import ResolutionContext


def test_resolution_context_preserves_request() -> None:
    request = Request(
        request_id="request-001",
        task_id="task.test",
    )

    context = ResolutionContext(request=request)

    assert context.request is request
