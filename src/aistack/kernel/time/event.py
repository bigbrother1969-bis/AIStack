from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TemporalEvent:
    """
    A generic event for any stream, not only the Kernel Runtime (whose
    events are `ExecutionTraceEvent`).

    `subject` names the component or stream concerned. `event_type` is a
    free string owned by the stream (`"cpu.decision.applied"`), not a
    shared enum. There is no timestamp: the history filename written by
    `write_artifact_with_history` already states the instant.
    """

    subject: str
    event_type: str
    message: str
