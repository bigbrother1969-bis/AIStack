from __future__ import annotations

from typing import Protocol


class Detector(Protocol):
    """
    What the monitor loop needs from a priority app's detector.

    `is_active()` is called once per poll and already includes the
    detector's own debounce and unreachable handling. The grace period on
    the way down (`aistack.priority.grace.resolve_boosted`) is applied by
    the monitor, not by the detector.
    """

    def is_active(self) -> bool: ...
