from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.gpu_threshold import (
    KINDS,
    MEMORY_PERCENT,
    TEMPERATURE_CELSIUS,
    UTILIZATION_PERCENT,
)


@dataclass(frozen=True)
class GpuAnomaly:
    """
    One GPU reading already found to cross the threshold `OPS-0007`
    declares for it.

    Mirrors `StorageShortage`: the reading and the threshold it was
    already found to cross, enforced here rather than only in the
    caller — the same reasoning `StorageShortage`'s own docstring
    gives. `evaluate_gpu` (`aistack.runtime.evaluate_gpu`) only ever
    receives an anomaly already confirmed to be one; it does not
    re-derive "too hot/busy/full" from a bare reading.

    `threshold_kind`/`threshold_value` are copied from the
    `GpuThreshold` that fired, not re-looked-up later — the same
    "state what fired, not what fires today" `StorageShortage
    .threshold_value` already holds.
    """

    reading: GpuReading
    threshold_kind: str
    threshold_value: float

    def __post_init__(self) -> None:
        if self.threshold_kind not in KINDS:
            raise ValueError(
                f"{self.reading.name} declares an unknown threshold kind "
                f"{self.threshold_kind!r}; OPS-0007 declares only {KINDS}"
            )

        observed = _observed_value(self.reading, self.threshold_kind)

        if observed < self.threshold_value:
            raise ValueError(
                f"{self.reading.name} reads {observed} for "
                f"{self.threshold_kind}, below its declared threshold of "
                f"{self.threshold_value}: this is not what the threshold "
                f"names as an anomaly"
            )


def _observed_value(reading: GpuReading, kind: str) -> float:
    if kind == TEMPERATURE_CELSIUS:
        return reading.temperature_celsius

    if kind == UTILIZATION_PERCENT:
        return reading.utilization_percent

    assert kind == MEMORY_PERCENT
    return reading.memory_percent
