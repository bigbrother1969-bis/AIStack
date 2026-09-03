from __future__ import annotations

from typing import Protocol


class Detector(Protocol):
    """
    What the monitor loop needs from any priority app's detector,
    and nothing more.

    One method, no state visible to the caller: `is_active()` is
    asked once per poll and answers with this instant's own
    reading, already folding in whatever debounce or unreachable-
    handling that detector's own type needs (`JellyfinDetector`'s
    decision #4 fallback, `CpuThresholdDetector`'s sustained-
    duration streak). The monitor's own smoothing —
    `aistack.priority.grace.resolve_boosted`'s 60-second
    grace-on-the-way-down — is layered on top of this answer, once
    per priority app, and does not belong to the detector itself.

    A `Protocol`, not a base class: `JellyfinDetector` and
    `CpuThresholdDetector` share no implementation, only this one
    shape, and a third detector type should never be required to
    inherit from anything to satisfy it.
    """

    def is_active(self) -> bool: ...
