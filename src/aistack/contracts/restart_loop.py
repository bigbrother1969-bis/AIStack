from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RestartLoop:
    """
    One container found dying and restarting over and over within a
    recent window — the restart loop `OPS-0004`'s third reference
    incident names, measured over time rather than at one instant.

    **Why it exists — 2026-10-02.** `arrstack/mularr` crashed at
    startup every ~17 seconds for three weeks (SQLite on NFS, 1,537
    restarts) and the Health Cockpit never flagged it: the Services
    domain reads each container's state at one instant
    (`ContainerStateReading`, the owner's v1 scope of 2026-09-11), and
    between two crashes mularr read as `running`. The docker-events
    collector had recorded every `die`/`start` all along. Owner's
    cadrage the same day: count recent restarts from that history,
    against a declared threshold.

    `container` is the event's stable subject (`compose_project/
    service`), `restarts` the number of `die` events Docker recorded for
    it within the last `window_minutes`, `threshold` the declared count
    it reached. A loop below its own threshold cannot be constructed —
    the same "a confirmed condition, not a bare reading" discipline
    `ContainerDistress` holds.
    """

    container: str
    restarts: int
    window_minutes: int
    threshold: int

    def __post_init__(self) -> None:
        if not self.container.strip():
            raise ValueError("a restart loop is about one container; this one names none")
        if self.window_minutes <= 0 or self.threshold <= 0:
            raise ValueError(
                f"{self.container}: window_minutes and threshold must be positive"
            )
        if self.restarts < self.threshold:
            raise ValueError(
                f"{self.container} restarted {self.restarts} time(s) in "
                f"{self.window_minutes} min, below its threshold of "
                f"{self.threshold}; that is not a restart loop"
            )
