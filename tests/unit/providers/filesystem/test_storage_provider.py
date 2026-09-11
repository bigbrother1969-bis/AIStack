from pathlib import Path

from aistack.providers.filesystem import StorageProvider


def test_a_real_mount_is_read(tmp_path: Path):

    provider = StorageProvider()

    readings = provider.collect_usage((str(tmp_path),))

    assert len(readings) == 1
    reading = readings[0]
    assert reading.mount == str(tmp_path)
    assert reading.total_bytes > 0
    assert reading.free_bytes >= 0


def test_a_mount_that_does_not_exist_is_skipped_not_raised_on():

    provider = StorageProvider()

    readings = provider.collect_usage(("/this/path/does/not/exist/anywhere",))

    assert readings == ()


def test_several_mounts_are_read_in_one_call(tmp_path: Path):

    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()

    provider = StorageProvider()

    readings = provider.collect_usage((str(a), str(b)))

    assert {reading.mount for reading in readings} == {str(a), str(b)}


def test_a_missing_mount_alongside_real_ones_is_silently_skipped(tmp_path: Path):

    provider = StorageProvider()

    readings = provider.collect_usage(
        (str(tmp_path), "/this/path/does/not/exist/anywhere")
    )

    assert len(readings) == 1
    assert readings[0].mount == str(tmp_path)
