from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.storage_threshold import FREE_BYTES, KINDS


@dataclass(frozen=True)
class StorageShortage:
    """
    One volume whose occupancy has already been found to cross the
    threshold `OPS-0005` declares for it.

    Mirrors `UnexplainedConsumption`: the reading and the threshold it
    was already found to cross, enforced here rather than only in the
    caller — the same reasoning `UnexplainedConsumption`'s own
    docstring gives for validating in the constructor. `evaluate_storage`
    (`aistack.runtime.evaluate_storage`) only ever receives a shortage
    already confirmed to be one; it does not re-derive "too full" from
    a bare reading.

    `threshold_kind`/`threshold_value` are copied from the
    `StorageThreshold` that fired, not re-looked-up later — the same
    "state what fired, not what fires today" `RuntimeFinding.signature`
    already holds.
    """

    reading: StorageReading
    threshold_kind: str
    threshold_value: float

    def __post_init__(self) -> None:
        if self.threshold_kind not in KINDS:
            raise ValueError(
                f"{self.reading.mount} declares an unknown threshold "
                f"kind {self.threshold_kind!r}; OPS-0005 declares only "
                f"{KINDS}"
            )

        if self.threshold_kind == FREE_BYTES:
            if self.reading.free_bytes > self.threshold_value:
                raise ValueError(
                    f"{self.reading.mount} has {self.reading.free_bytes} "
                    f"bytes free, above its declared threshold of "
                    f"{self.threshold_value}: this is not what the "
                    f"threshold names as a shortage"
                )
        else:
            if self.reading.percent_used < self.threshold_value:
                raise ValueError(
                    f"{self.reading.mount} reads "
                    f"{self.reading.percent_used}% occupied, below its "
                    f"declared threshold of {self.threshold_value}%: "
                    f"this is not what the threshold names as a shortage"
                )
