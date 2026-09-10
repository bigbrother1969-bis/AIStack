from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TemporalEvent:
    """
    Governed event contract — J3, Time Foundation
    (`claude/PLAN-J3-TIME-FOUNDATION-2026-09-10.md`).

    **Generalizes `aistack.kernel.tracing.event.ExecutionTraceEvent`,
    it does not replace it.** That type stays exactly as it is —
    Runtime-specific, with its own `phase`/`event_type` enums tied to
    the four fixed stages a `Request` goes through. This is the
    broader shape a stream that is *not* the Kernel Runtime (a CPU
    decision, a knowledge artifact's lifecycle change) also needs to
    describe an event, without extending `ExecutionPhase` — a closed
    enum scoped to Request/Resolution/Execution/Observation — with
    values that have nothing to do with a Runtime request.

    `subject` names the component or stream the event concerns
    (`ExecutionTraceEvent.component`'s equivalent). `event_type` is a
    free string owned by whichever stream raises the event
    (`"request.received"`, `"cpu.decision.applied"`,
    `"knowledge.validated"`) rather than a value drawn from one
    shared enum every stream would otherwise have to extend — the
    same reasoning that already led `ExecutionTraceEventType` to be
    scoped to the Runtime alone rather than shared.

    **No timestamp field, by the same reasoning
    `serialize_execution_trace` already documents for
    `ExecutionTrace`/`ExecutionTraceEvent`**: the instant an event
    was recorded is the one `write_artifact_with_history` already
    encodes in the history filename it gives the artifact this event
    ends up embedded in. A second, independent timestamp on the
    event itself would be one more fact that can drift from the one
    the filename already states — true for every stream, not only
    Runtime execution, so this contract keeps the same discipline
    rather than reopening the question per stream.
    """

    subject: str
    event_type: str
    message: str
