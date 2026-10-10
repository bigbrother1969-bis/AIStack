from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.storage_threshold import FREE_BYTES, KINDS


@dataclass(frozen=True)
class StorageShortage:
    """
    A volume whose occupancy crosses its OPS-0005 threshold; the
    constructor checks it.

    `threshold_kind`/`threshold_value` are copied from the threshold
    that fired, so the shortage states what fired then.
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
