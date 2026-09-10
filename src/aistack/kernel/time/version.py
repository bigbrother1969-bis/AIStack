from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class VersionId:
    """
    Governed version identifier — J3, Time Foundation
    (`claude/PLAN-J3-TIME-FOUNDATION-2026-09-10.md`).

    **Replaces the bare `version: int` field of
    `aistack.kernel.knowledge.artifact.model.KnowledgeArtifact`** —
    the only place in this heritage that carried any notion of
    "version" before this patch, and an unwired one: nothing ever
    assigned it except a unit test setting `version=1` by hand.
    Every other historicised artifact (Observation History, Runtime
    Operation History, the CPU decision history) has never had a
    version at all, identified only by the instant
    `write_artifact_with_history` stamped into its filename.

    `subject` scopes the sequence — "this container's CPU decision",
    "this Runtime request's trace" — the same idea `VersionSequence`
    below turns into a real counter, rather than a single global
    version space where an unrelated stream's writes would advance
    a number this one has no reason to share.

    A `VersionId` is a value, not a counter — see `VersionSequence`
    for how one is produced. Constructing one directly with an
    arbitrary `sequence` is possible (it is a plain frozen dataclass,
    like every other contract in this heritage) but is exactly the
    "assigned by hand" failure mode this contract exists to move
    away from; real callers go through `VersionSequence.next()`.
    """

    subject: str
    sequence: int


@dataclass
class VersionSequence:
    """
    In-memory, per-subject monotonic counter handing out
    `VersionId`s — the governed generator `VersionId`'s own docstring
    points to, so a version is produced rather than assigned by hand.

    **Deliberately in-memory only, for now.** Every real caller J3
    absorbs onto this foundation (`FileTraceRepository`,
    `decision_history.record_decision`) runs inside a short-lived CLI
    process — a fresh `VersionSequence` per process would hand out
    `sequence=1` on every single run, which is not what "monotonic"
    is supposed to mean once the process restarts. Making the
    sequence durable across process restarts (for instance, by
    seeding it from `aistack.history.query.available_instants`'s own
    count for that subject, so the filesystem history already written
    is the source of truth rather than a second counter that could
    drift from it) is left to the step that actually wires a
    `VersionSequence` into `FileTraceRepository`/`decision_history` —
    not decided here, where only the contract is being introduced.
    """

    _next: dict[str, int] = field(default_factory=dict)

    def next(self, subject: str) -> VersionId:
        sequence = self._next.get(subject, 0) + 1
        self._next[subject] = sequence

        return VersionId(subject=subject, sequence=sequence)
