from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RestartLoop:
    """
    A container that died and restarted repeatedly within a recent
    window (OPS-0004), counted from recorded Docker `die` events.

    An instant reading misses this: between two crashes the container
    reads as `running`. `container` is `compose_project/service`;
    `restarts` counts `die` events in the last `window_minutes`. A loop
    below its `threshold` cannot be constructed.
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
