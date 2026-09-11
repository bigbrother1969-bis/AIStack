import pytest

from aistack.contracts.storage_reading import StorageReading


def test_a_reading_requires_a_mount():

    with pytest.raises(ValueError, match="names none"):
        StorageReading(mount="", total_bytes=100, used_bytes=50, free_bytes=50)


def test_a_reading_refuses_negative_bytes():

    with pytest.raises(ValueError, match="negative"):
        StorageReading(mount="/", total_bytes=100, used_bytes=-1, free_bytes=50)


def test_used_plus_free_may_not_exceed_total():

    with pytest.raises(ValueError, match="exceeding"):
        StorageReading(mount="/", total_bytes=100, used_bytes=80, free_bytes=30)


def test_used_plus_free_below_total_is_allowed():
    """
    Filesystems reserve blocks — ext4's default 5% — that are
    neither used nor free in what this type reports. Equality is
    never required.
    """

    reading = StorageReading(
        mount="/", total_bytes=100, used_bytes=70, free_bytes=25
    )

    assert reading.free_bytes == 25


def test_percent_used_is_computed_from_total():

    reading = StorageReading(
        mount="/dev/sdc1", total_bytes=200, used_bytes=146, free_bytes=54
    )

    assert reading.percent_used == 73.0


def test_percent_used_is_zero_for_a_volume_with_no_reported_capacity():

    reading = StorageReading(mount="/", total_bytes=0, used_bytes=0, free_bytes=0)

    assert reading.percent_used == 0.0
