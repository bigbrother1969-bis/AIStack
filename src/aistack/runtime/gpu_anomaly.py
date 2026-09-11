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
    Which GPU readings have crossed a threshold `OPS-0007` declares.

    Mirrors `find_storage_shortage`: given readings already collected
    and thresholds already declared, decides which ones actually
    qualify — it never proposes a threshold itself.

    **Every reading is checked against every declared threshold kind**
    — unlike `find_storage_shortage`, which keys a threshold to one
    `mount` among several, a `GpuThreshold` names no card of its own
    (`GpuThreshold`'s own docstring: v1 scope is one GPU per host), so
    there is no per-reading key to match on. A threshold kind never
    declared for this host is simply never checked — the same "not
    measured is not zero" convention `find_storage_shortage` already
    holds for a mount with no declared threshold.

    A reading may produce zero, one, two or three anomalies — one per
    threshold kind it crosses, independent of the others.

    Pure: readings and thresholds already collected in, anomalies out
    — the same discipline `find_storage_shortage` already holds.
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
