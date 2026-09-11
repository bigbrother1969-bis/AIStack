import pytest

from aistack.contracts.gpu_threshold import (
    KINDS,
    MEMORY_PERCENT,
    TEMPERATURE_CELSIUS,
    UTILIZATION_PERCENT,
    GpuThreshold,
    GpuThresholdRegister,
    HostGpuThresholds,
)


def test_only_three_kinds_are_declared():
    assert KINDS == (TEMPERATURE_CELSIUS, UTILIZATION_PERCENT, MEMORY_PERCENT)


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="unknown GPU threshold kind"):
        GpuThreshold(kind="power_watts", value=100.0)


def test_a_negative_value_is_refused():
    with pytest.raises(ValueError, match="cannot be negative"):
        GpuThreshold(kind=TEMPERATURE_CELSIUS, value=-1.0)


def test_a_valid_threshold_is_accepted():
    threshold = GpuThreshold(kind=TEMPERATURE_CELSIUS, value=80.0)

    assert threshold.kind == TEMPERATURE_CELSIUS
    assert threshold.value == 80.0


def test_a_host_thresholds_names_no_host_is_refused():
    with pytest.raises(ValueError, match="name no host"):
        HostGpuThresholds(host="", thresholds=())


def test_for_host_returns_the_matching_entry():
    gigabyte = HostGpuThresholds(
        host="GIGABYTE",
        thresholds=(GpuThreshold(kind=TEMPERATURE_CELSIUS, value=80.0),),
    )
    register = GpuThresholdRegister(hosts=(gigabyte,))

    assert register.for_host("GIGABYTE") == gigabyte.thresholds


def test_for_host_returns_empty_for_an_undeclared_host():
    register = GpuThresholdRegister(hosts=())

    assert register.for_host("raspberry") == ()
