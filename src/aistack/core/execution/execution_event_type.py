from enum import Enum


class ExecutionEventType(str, Enum):
    EXECUTION_STARTED = "execution_started"
    EXECUTION_FINISHED = "execution_finished"

    PHASE_STARTED = "phase_started"
    PHASE_FINISHED = "phase_finished"

    PROGRESS = "progress"

    WARNING = "warning"
    ERROR = "error"

    RESOURCE_SNAPSHOT = "resource_snapshot"

    CHECKPOINT = "checkpoint"

    ARTIFACT_GENERATED = "artifact_generated"
