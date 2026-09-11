from aistack.contracts.storage_reading import StorageReading
from aistack.contracts.storage_threshold import (
    FREE_BYTES,
    PERCENT_USED,
    StorageThreshold,
)
from aistack.runtime.storage_shortage import find_storage_shortage


def reading(mount: str, total: int, used: int, free: int) -> StorageReading:
    return StorageReading(
        mount=mount, total_bytes=total, used_bytes=used, free_bytes=free
    )


def test_a_free_bytes_volume_below_threshold_is_flagged():

    gigabyte_root = reading("/", 212 * 1024**3, 202 * 1024**3, 10 * 1024**3)

    shortages = find_storage_shortage(
        [gigabyte_root],
        [StorageThreshold(mount="/", kind=FREE_BYTES, value=20 * 1024**3)],
    )

    assert len(shortages) == 1
    assert shortages[0].reading.mount == "/"


def test_a_free_bytes_volume_above_threshold_is_not_flagged():

    gigabyte_root = reading("/", 212 * 1024**3, 156 * 1024**3, 56 * 1024**3)

    shortages = find_storage_shortage(
        [gigabyte_root],
        [StorageThreshold(mount="/", kind=FREE_BYTES, value=20 * 1024**3)],
    )

    assert shortages == ()


def test_exactly_at_the_free_bytes_threshold_is_flagged():

    reading_at_threshold = reading(
        "/", 212 * 1024**3, 192 * 1024**3, 20 * 1024**3
    )

    shortages = find_storage_shortage(
        [reading_at_threshold],
        [StorageThreshold(mount="/", kind=FREE_BYTES, value=20 * 1024**3)],
    )

    assert len(shortages) == 1


def test_a_percent_used_volume_at_or_above_threshold_is_flagged():

    films = reading("/media/Films", 100, 92, 8)

    shortages = find_storage_shortage(
        [films],
        [StorageThreshold(mount="/media/Films", kind=PERCENT_USED, value=90.0)],
    )

    assert len(shortages) == 1
    assert shortages[0].threshold_kind == PERCENT_USED


def test_a_percent_used_volume_below_threshold_is_not_flagged():

    films = reading("/media/Films", 100, 64, 36)

    shortages = find_storage_shortage(
        [films],
        [StorageThreshold(mount="/media/Films", kind=PERCENT_USED, value=90.0)],
    )

    assert shortages == ()


def test_a_mount_with_no_declared_threshold_is_silently_not_evaluated():

    undeclared = reading("/boot/firmware", 100, 99, 1)

    shortages = find_storage_shortage([undeclared], [])

    assert shortages == ()


def test_only_the_mount_crossing_its_own_threshold_is_flagged_in_a_batch():

    gigabyte_root = reading("/", 212 * 1024**3, 202 * 1024**3, 10 * 1024**3)
    films = reading("/media/Films", 1800, 1152, 648)

    shortages = find_storage_shortage(
        [gigabyte_root, films],
        [
            StorageThreshold(mount="/", kind=FREE_BYTES, value=20 * 1024**3),
            StorageThreshold(mount="/media/Films", kind=PERCENT_USED, value=90.0),
        ],
    )

    assert [s.reading.mount for s in shortages] == ["/"]


def test_an_empty_reading_set_flags_nothing():

    assert (
        find_storage_shortage(
            [], [StorageThreshold(mount="/", kind=FREE_BYTES, value=1.0)]
        )
        == ()
    )
