from aistack.kernel.resolution import ResolutionResult


class DummyTask:
    pass


def test_resolution_result_preserves_explanation() -> None:
    task = DummyTask()

    result = ResolutionResult(
        task=task,
        resolver="TaskResolver",
        reason="Selected by identifier",
    )

    assert result.task is task
    assert result.resolver == "TaskResolver"
    assert result.reason == "Selected by identifier"
