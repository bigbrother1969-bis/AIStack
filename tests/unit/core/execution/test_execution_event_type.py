from aistack.core.execution.execution_event_type import ExecutionEventType


def test_execution_event_type_values():
    assert ExecutionEventType.EXECUTION_STARTED.value == "execution_started"
    assert ExecutionEventType.EXECUTION_FINISHED.value == "execution_finished"

    assert ExecutionEventType.PHASE_STARTED.value == "phase_started"
    assert ExecutionEventType.PHASE_FINISHED.value == "phase_finished"

    assert ExecutionEventType.PROGRESS.value == "progress"

    assert ExecutionEventType.WARNING.value == "warning"
    assert ExecutionEventType.ERROR.value == "error"

    assert (
        ExecutionEventType.RESOURCE_SNAPSHOT.value
        == "resource_snapshot"
    )

    assert ExecutionEventType.CHECKPOINT.value == "checkpoint"

    assert (
        ExecutionEventType.ARTIFACT_GENERATED.value
        == "artifact_generated"
    )
