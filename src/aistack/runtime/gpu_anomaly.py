from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.gpu_anomaly import GpuAnomaly
from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.gpu_threshold import (
    GpuThreshold,
    MEMORY_PERCENT,
    TEMPERATURE_CELSIUS,
    UTILIZATION_PERCENT,
)


def find_gpu_anomalies(
    readings: Sequence[GpuReading],
    thresholds: Sequence[GpuThreshold],
) -> tuple[GpuAnomaly, ...]:
    """
    Return the GPU readings that cross a threshold declared under `OPS-0007`.

    A `GpuThreshold` names no card (one GPU per host), so every reading is
    checked against every declared threshold kind. A kind not declared is
    never checked. A reading yields one anomaly per threshold kind it crosses.
    """

    anomalies: list[GpuAnomaly] = []

    for reading in readings:
        for threshold in thresholds:
            observed = _observed_value(reading, threshold.kind)

            if observed < threshold.value:
                continue

            anomalies.append(
                GpuAnomaly(
                    reading=reading,
                    threshold_kind=threshold.kind,
                    threshold_value=threshold.value,
                )
            )

    return tuple(anomalies)


def _observed_value(reading: GpuReading, kind: str) -> float:
    if kind == TEMPERATURE_CELSIUS:
        return reading.temperature_celsius

    if kind == UTILIZATION_PERCENT:
        return reading.utilization_percent

    assert kind == MEMORY_PERCENT
    return reading.memory_percent
