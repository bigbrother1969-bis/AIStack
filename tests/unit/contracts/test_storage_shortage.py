import pytest

from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.storage_shortage import StorageShortage
from aistack.contracts.storage_threshold import (
    FREE_BYTES,
    PERCENT_USED,
    StorageThreshold,
)


# --------------------------------------------------------------------
# `StorageThreshold`
# --------------------------------------------------------------------


def test_a_threshold_requires_a_mount():

    with pytest.raises(ValueError, match="names none"):
        StorageThreshold(mount="", kind=FREE_BYTES, value=1.0)


def test_a_threshold_refuses_an_unknown_kind():

    with pytest.raises(ValueError, match="unknown threshold kind"):
        StorageThreshold(mount="/", kind="percent_free", value=10.0)


def test_a_threshold_refuses_a_negative_value():

    with pytest.raises(ValueError, match="negative"):
        StorageThreshold(mount="/", kind=FREE_BYTES, value=-1.0)


# --------------------------------------------------------------------
# `StorageShortage`
# --------------------------------------------------------------------


def gigabyte_root(free_bytes: int = 5 * 1024**3) -> StorageReading:
    total = 212 * 1024**3
    return StorageReading(
        mount="/", total_bytes=total, used_bytes=total - free_bytes, free_bytes=free_bytes
    )


def test_a_free_bytes_shortage_is_accepted_when_free_is_at_or_below_threshold():

    shortage = StorageShortage(
        reading=gigabyte_root(free_bytes=10 * 1024**3),
        threshold_kind=FREE_BYTES,
        threshold_value=20 * 1024**3,
    )

    assert shortage.reading.free_bytes == 10 * 1024**3


def test_a_free_bytes_reading_above_threshold_is_refused_by_its_own_contract():
    """
    Mirrors `UnexplainedConsumption`'s own enforcement: a shortage
    that is not actually short cannot be constructed.
    """

    with pytest.raises(ValueError, match="not what the threshold names"):
        StorageShortage(
            reading=gigabyte_root(free_bytes=56 * 1024**3),
            threshold_kind=FREE_BYTES,
            threshold_value=20 * 1024**3,
        )


def test_a_percent_used_shortage_is_accepted_when_at_or_above_threshold():

    reading = StorageReading(
        mount="/media/Films",
        total_bytes=100,
        used_bytes=92,
        free_bytes=8,
    )

    shortage = StorageShortage(
        reading=reading, threshold_kind=PERCENT_USED, threshold_value=90.0
    )

    assert shortage.threshold_value == 90.0


def test_a_percent_used_reading_below_threshold_is_refused():

    reading = StorageReading(
        mount="/media/Films", total_bytes=100, used_bytes=64, free_bytes=36
    )

    with pytest.raises(ValueError, match="not what the threshold names"):
        StorageShortage(
            reading=reading, threshold_kind=PERCENT_USED, threshold_value=90.0
        )
