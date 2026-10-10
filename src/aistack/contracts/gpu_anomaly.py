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
    A GPU reading at or above an OPS-0007 threshold; the constructor
    checks it.

    `threshold_kind`/`threshold_value` are copied from the threshold
    that fired, so the anomaly states what fired then.
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
