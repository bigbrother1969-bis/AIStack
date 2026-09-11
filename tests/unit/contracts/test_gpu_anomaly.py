from datetime import datetime, timezone

import pytest

from aistack.contracts.gpu_anomaly import GpuAnomaly
from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.gpu_threshold import (
    MEMORY_PERCENT,
    TEMPERATURE_CELSIUS,
    UTILIZATION_PERCENT,
)

NAME = "Quadro P400"


def reading(
    utilization_percent: float = 1.0,
    memory_used_mib: float = 142.0,
    memory_total_mib: float = 2048.0,
    temperature_celsius: float = 49.0,
) -> GpuReading:
    return GpuReading(
        name=NAME,
        observed_at=datetime.now(timezone.utc),
        utilization_percent=utilization_percent,
        memory_used_mib=memory_used_mib,
        memory_total_mib=memory_total_mib,
        temperature_celsius=temperature_celsius,
    )


def test_an_unknown_threshold_kind_is_refused():
    with pytest.raises(ValueError, match="unknown threshold kind"):
        GpuAnomaly(
            reading=reading(),
            threshold_kind="power_watts",
            threshold_value=100.0,
        )


def test_temperature_below_threshold_is_refused():
    with pytest.raises(ValueError, match="not what the threshold names"):
        GpuAnomaly(
            reading=reading(temperature_celsius=49.0),
            threshold_kind=TEMPERATURE_CELSIUS,
            threshold_value=80.0,
        )


def test_temperature_at_or_above_threshold_is_accepted():
    anomaly = GpuAnomaly(
        reading=reading(temperature_celsius=85.0),
        threshold_kind=TEMPERATURE_CELSIUS,
        threshold_value=80.0,
    )

    assert anomaly.threshold_kind == TEMPERATURE_CELSIUS


def test_temperature_exactly_at_the_threshold_boundary_is_accepted():
    """
    Mirrors `find_storage_shortage`'s own "at or above" convention —
    unlike backup's strict "past the boundary" one.
    """

    anomaly = GpuAnomaly(
        reading=reading(temperature_celsius=80.0),
        threshold_kind=TEMPERATURE_CELSIUS,
        threshold_value=80.0,
    )

    assert anomaly.threshold_value == 80.0


def test_utilization_below_threshold_is_refused():
    with pytest.raises(ValueError, match="not what the threshold names"):
        GpuAnomaly(
            reading=reading(utilization_percent=50.0),
            threshold_kind=UTILIZATION_PERCENT,
            threshold_value=90.0,
        )


def test_utilization_at_or_above_threshold_is_accepted():
    anomaly = GpuAnomaly(
        reading=reading(utilization_percent=95.0),
        threshold_kind=UTILIZATION_PERCENT,
        threshold_value=90.0,
    )

    assert anomaly.threshold_kind == UTILIZATION_PERCENT


def test_memory_below_threshold_is_refused():
    with pytest.raises(ValueError, match="not what the threshold names"):
        GpuAnomaly(
            reading=reading(memory_used_mib=142.0, memory_total_mib=2048.0),
            threshold_kind=MEMORY_PERCENT,
            threshold_value=90.0,
        )


def test_memory_at_or_above_threshold_is_accepted():
    anomaly = GpuAnomaly(
        reading=reading(memory_used_mib=1900.0, memory_total_mib=2048.0),
        threshold_kind=MEMORY_PERCENT,
        threshold_value=90.0,
    )

    assert anomaly.threshold_kind == MEMORY_PERCENT
