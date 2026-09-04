import pytest

from aistack.contracts.temperature_reading import TemperatureReading


def test_a_reading_requires_a_sensor():

    with pytest.raises(ValueError, match="names none"):
        TemperatureReading(sensor="", celsius=70.5)


def test_thresholds_default_to_absent():

    reading = TemperatureReading(sensor="k10temp-pci-00c3/temp1", celsius=40.0)

    assert reading.high_celsius is None
    assert reading.critical_celsius is None
    assert reading.at_or_above_high is None
    assert reading.at_or_above_critical is None


def test_a_reading_below_its_own_high_threshold():

    reading = TemperatureReading(
        sensor="k10temp-pci-00c3/temp1",
        celsius=40.0,
        high_celsius=70.0,
        critical_celsius=72.0,
    )

    assert reading.at_or_above_high is False
    assert reading.at_or_above_critical is False


def test_the_reading_captured_live_on_gigabyte_reads_at_or_above_high():
    """
    `sensors`, run live on GIGABYTE 2026-09-04: temp1 read 70.5 °C
    against the chip's own declared high of 70.0 °C — already at
    the hardware's own limit, not merely close to it.
    """

    reading = TemperatureReading(
        sensor="k10temp-pci-00c3/temp1",
        celsius=70.5,
        high_celsius=70.0,
        critical_celsius=72.0,
    )

    assert reading.at_or_above_high is True
    assert reading.at_or_above_critical is False
