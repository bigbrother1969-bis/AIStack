import os
import time
from pathlib import Path

import pytest

from aistack.providers.filesystem import BackupProvider


def test_a_path_that_does_not_exist_is_skipped_not_raised_on():
    """
    Mirrors `StorageProvider.collect_usage`'s "never raises"
    convention for a mount that is not currently reachable at all.
    """

    provider = BackupProvider()

    readings = provider.collect_freshness(("/this/path/does/not/exist/anywhere",))

    assert readings == ()


def test_a_path_that_exists_but_holds_no_file_still_produces_a_reading(
    tmp_path: Path,
):
    """
    **The deliberate refinement over `StorageProvider`'s convention.**
    A directory that exists but has never received a backup file is
    itself the fact this domain exists to surface — silently skipping
    it the way an absent mount is skipped would drop the one case the
    owner asked this domain to catch.
    """

    empty = tmp_path / "wordpress"
    empty.mkdir()

    provider = BackupProvider()

    readings = provider.collect_freshness((str(empty),))

    assert len(readings) == 1
    assert readings[0].path == str(empty)
    assert readings[0].newest_file_mtime is None


def test_the_newest_file_among_several_is_reported(tmp_path: Path):

    directory = tmp_path / "wordpress"
    directory.mkdir()

    older = directory / "backup-2026-09-01.tar.gz"
    newer = directory / "backup-2026-09-08.tar.gz"
    older.write_text("older")
    newer.write_text("newer")

    now = int(time.time())
    os.utime(older, (now - 7 * 86400, now - 7 * 86400))
    os.utime(newer, (now - 1 * 86400, now - 1 * 86400))

    provider = BackupProvider()

    readings = provider.collect_freshness((str(directory),))

    assert len(readings) == 1
    assert readings[0].newest_file_mtime is not None
    assert readings[0].newest_file_mtime.timestamp() == pytest.approx(now - 86400)


def test_a_file_nested_in_a_subdirectory_is_found(tmp_path: Path):

    directory = tmp_path / "wordpress"
    nested = directory / "2026" / "09"
    nested.mkdir(parents=True)
    backup_file = nested / "backup.tar.gz"
    backup_file.write_text("data")

    provider = BackupProvider()

    readings = provider.collect_freshness((str(directory),))

    assert len(readings) == 1
    assert readings[0].newest_file_mtime is not None


def test_a_missing_path_alongside_a_real_one_is_silently_skipped(tmp_path: Path):

    real = tmp_path / "wordpress"
    real.mkdir()

    provider = BackupProvider()

    readings = provider.collect_freshness(
        (str(real), "/this/path/does/not/exist/anywhere")
    )

    assert len(readings) == 1
    assert readings[0].path == str(real)


def test_several_paths_are_read_in_one_call(tmp_path: Path):

    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    (a / "backup.tar.gz").write_text("data")

    provider = BackupProvider()

    readings = provider.collect_freshness((str(a), str(b)))

    by_path = {reading.path: reading for reading in readings}
    assert len(by_path) == 2
    assert by_path[str(a)].newest_file_mtime is not None
    assert by_path[str(b)].newest_file_mtime is None
