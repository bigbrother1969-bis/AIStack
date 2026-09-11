from datetime import datetime, timezone

from aistack.contracts.gpu_reading import GpuReading
from aistack.contracts.gpu_threshold import (
    MEMORY_PERCENT,
    TEMPERATURE_CELSIUS,
    UTILIZATION_PERCENT,
    GpuThreshold,
)
from aistack.runtime.gpu_anomaly import find_gpu_anomalies

NAME = "Quadro P400"


def reading(
    name: str = NAME,
    utilization_percent: float = 1.0,
    memory_used_mib: float = 142.0,
    memory_total_mib: float = 2048.0,
    temperature_celsius: float = 49.0,
) -> GpuReading:
    return GpuReading(
        name=name,
        observed_at=datetime.now(timezone.utc),
        utilization_percent=utilization_percent,
        memory_used_mib=memory_used_mib,
        memory_total_mib=memory_total_mib,
        temperature_celsius=temperature_celsius,
    )


TEMP_THRESHOLD = GpuThreshold(kind=TEMPERATURE_CELSIUS, value=80.0)
UTIL_THRESHOLD = GpuThreshold(kind=UTILIZATION_PERCENT, value=90.0)
MEM_THRESHOLD = GpuThreshold(kind=MEMORY_PERCENT, value=90.0)


def test_a_clean_reading_flags_nothing():
    anomalies = find_gpu_anomalies(
        [reading()], [TEMP_THRESHOLD, UTIL_THRESHOLD, MEM_THRESHOLD]
    )

    assert anomalies == ()


def test_a_hot_reading_is_flagged_on_temperature():
    anomalies = find_gpu_anomalies(
        [reading(temperature_celsius=85.0)], [TEMP_THRESHOLD]
    )

    assert len(anomalies) == 1
    assert anomalies[0].threshold_kind == TEMPERATURE_CELSIUS


def test_a_busy_reading_is_flagged_on_utilization():
    anomalies = find_gpu_anomalies(
        [reading(utilization_percent=95.0)], [UTIL_THRESHOLD]
    )

    assert len(anomalies) == 1
    assert anomalies[0].threshold_kind == UTILIZATION_PERCENT


def test_a_full_reading_is_flagged_on_memory():
    anomalies = find_gpu_anomalies(
        [reading(memory_used_mib=1900.0, memory_total_mib=2048.0)],
        [MEM_THRESHOLD],
    )

    assert len(anomalies) == 1
    assert anomalies[0].threshold_kind == MEMORY_PERCENT


def test_one_reading_can_cross_several_kinds_at_once():
    anomalies = find_gpu_anomalies(
        [
            reading(
                temperature_celsius=85.0,
                utilization_percent=95.0,
                memory_used_mib=1900.0,
                memory_total_mib=2048.0,
            )
        ],
        [TEMP_THRESHOLD, UTIL_THRESHOLD, MEM_THRESHOLD],
    )

    assert {a.threshold_kind for a in anomalies} == {
        TEMPERATURE_CELSIUS,
        UTILIZATION_PERCENT,
        MEMORY_PERCENT,
    }


def test_a_threshold_kind_never_declared_is_never_checked():
    anomalies = find_gpu_anomalies(
        [reading(utilization_percent=99.0)], [TEMP_THRESHOLD]
    )

    assert anomalies == ()


def test_exactly_at_the_threshold_boundary_is_flagged():
    """
    Mirrors `find_storage_shortage`'s own "at or above" convention.
    """

    anomalies = find_gpu_anomalies([reading(temperature_celsius=80.0)], [TEMP_THRESHOLD])

    assert len(anomalies) == 1


def test_an_empty_reading_set_flags_nothing():
    assert find_gpu_anomalies([], [TEMP_THRESHOLD]) == ()


def test_an_empty_threshold_set_flags_nothing():
    assert find_gpu_anomalies([reading(temperature_celsius=99.0)], []) == ()
