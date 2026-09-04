import pytest

from aistack.contracts.cpu_reduction import CpuReductionMeasurement


def test_a_measurement_requires_a_subject():

    with pytest.raises(ValueError, match="names none"):
        CpuReductionMeasurement(
            subject="",
            before_percent=58.0,
            after_percent=0.32,
            before_reference="x",
            after_reference="y",
        )


def test_before_percent_must_be_positive():

    with pytest.raises(ValueError, match="nothing to measure a drop against"):
        CpuReductionMeasurement(
            subject="x",
            before_percent=0.0,
            after_percent=0.0,
            before_reference="a",
            after_reference="b",
        )


def test_after_percent_must_not_be_negative():

    with pytest.raises(ValueError, match="not a CPU percentage"):
        CpuReductionMeasurement(
            subject="x",
            before_percent=10.0,
            after_percent=-1.0,
            before_reference="a",
            after_reference="b",
        )


def test_after_exceeding_before_is_refused():
    """
    A rise dressed up as a measurement is not what this class exists
    to certify.
    """

    with pytest.raises(ValueError, match="not a reduction"):
        CpuReductionMeasurement(
            subject="x",
            before_percent=10.0,
            after_percent=20.0,
            before_reference="a",
            after_reference="b",
        )


def test_a_before_reading_requires_its_own_reference():

    with pytest.raises(ValueError, match="before-reading carries no"):
        CpuReductionMeasurement(
            subject="x",
            before_percent=10.0,
            after_percent=1.0,
            before_reference="",
            after_reference="b",
        )


def test_an_after_reading_requires_its_own_reference():

    with pytest.raises(ValueError, match="after-reading carries no"):
        CpuReductionMeasurement(
            subject="x",
            before_percent=10.0,
            after_percent=1.0,
            before_reference="a",
            after_reference="",
        )


def test_a_reduction_under_the_threshold_does_not_meet_it():

    measurement = CpuReductionMeasurement(
        subject="x",
        before_percent=10.0,
        after_percent=2.0,
        before_reference="a",
        after_reference="b",
    )

    assert round(measurement.reduction_percent, 1) == 80.0
    assert measurement.meets_threshold is False


def test_the_reference_incidents_upper_bound_meets_the_threshold():
    """
    `docker-compose.selection-ui.yml`'s own comment: 58 % (the upper
    bound of `STD-0300` § VS-4's reference incident) to 0.32 %
    (measured after two minutes of inactivity) is a 99.4 % reduction
    — the exact figure that comment already names.
    """

    measurement = CpuReductionMeasurement(
        subject="aistack-selection-ui",
        before_percent=58.0,
        after_percent=0.32,
        before_reference="STD-0300 § VS-4 reference incident",
        after_reference="docker-compose.selection-ui.yml: idle CPU",
    )

    assert round(measurement.reduction_percent, 1) == 99.4
    assert measurement.meets_threshold is True


def test_the_reference_incidents_lower_bound_also_meets_the_threshold():

    measurement = CpuReductionMeasurement(
        subject="aistack-selection-ui",
        before_percent=48.0,
        after_percent=0.32,
        before_reference="STD-0300 § VS-4 reference incident",
        after_reference="docker-compose.selection-ui.yml: idle CPU",
    )

    assert measurement.meets_threshold is True


def test_the_threshold_is_configurable_but_defaults_to_95():

    measurement = CpuReductionMeasurement(
        subject="x",
        before_percent=10.0,
        after_percent=2.0,
        before_reference="a",
        after_reference="b",
    )

    assert measurement.threshold_percent == 95.0
