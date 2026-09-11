from datetime import datetime, timezone

import pytest

from aistack.contracts.gpu_reading import GpuReading

NAME = "Quadro P400"


def reading(
    utilization_percent: float = 0.0,
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


def test_a_reading_names_no_card_is_refused():
    with pytest.raises(ValueError, match="names none"):
        GpuReading(
            name="",
            observed_at=datetime.now(timezone.utc),
            utilization_percent=0.0,
            memory_used_mib=0.0,
            memory_total_mib=2048.0,
            temperature_celsius=49.0,
        )


def test_utilization_above_100_is_refused():
    with pytest.raises(ValueError, match="outside the 0-100 range"):
        reading(utilization_percent=101.0)


def test_utilization_below_0_is_refused():
    with pytest.raises(ValueError, match="outside the 0-100 range"):
        reading(utilization_percent=-1.0)


def test_a_negative_memory_used_is_refused():
    with pytest.raises(ValueError, match="negative memory figure"):
        reading(memory_used_mib=-1.0)


def test_a_negative_memory_total_is_refused():
    with pytest.raises(ValueError, match="negative memory figure"):
        reading(memory_total_mib=-1.0)


def test_memory_used_exceeding_total_is_refused():
    with pytest.raises(ValueError, match="exceeding its own reported total"):
        reading(memory_used_mib=3000.0, memory_total_mib=2048.0)


def test_memory_percent_is_derived():
    one = reading(memory_used_mib=1024.0, memory_total_mib=2048.0)

    assert one.memory_percent == 50.0


def test_memory_percent_is_zero_when_total_is_zero():
    one = reading(memory_used_mib=0.0, memory_total_mib=0.0)

    assert one.memory_percent == 0.0


def test_the_real_baseline_reading_is_valid():
    """
    The exact live `nvidia-smi` values taken on GIGABYTE, 2026-09-11
    (`OPS-0007` § *Provenance*) — an idle desktop GPU, no AI workload.
    """

    one = reading(
        utilization_percent=1.0,
        memory_used_mib=142.0,
        memory_total_mib=2048.0,
        temperature_celsius=49.0,
    )

    assert one.name == NAME
    assert one.memory_percent == pytest.approx(6.93, abs=0.01)
