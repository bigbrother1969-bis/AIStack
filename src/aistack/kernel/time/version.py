from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class VersionId:
    """
    A version identifier: a sequence number scoped to one `subject`
    (e.g. one container's CPU decisions), not a global counter.

    A value, not a counter: produce one with `VersionSequence.next()` or
    `next_version_from_history`, not by hand.
    """

    subject: str
    sequence: int


@dataclass
class VersionSequence:
    """
    In-memory, per-subject monotonic counter of `VersionId`s.

    It restarts at 1 in each process; short-lived processes use
    `next_version_from_history`, which counts history on disk.
    """

    _next: dict[str, int] = field(default_factory=dict)

    def next(self, subject: str) -> VersionId:
        sequence = self._next.get(subject, 0) + 1
        self._next[subject] = sequence

        return VersionId(subject=subject, sequence=sequence)
