from datetime import datetime, timedelta, timezone

import pytest

from aistack.contracts.backup_reading import BackupReading


def test_a_reading_requires_a_path():

    with pytest.raises(ValueError, match="names none"):
        BackupReading(path="", observed_at=datetime.now(timezone.utc))


def test_a_reading_may_carry_no_backup_file_at_all():
    """
    `newest_file_mtime` defaults to `None` — "no backup file found",
    the fact this domain exists to surface, not an omission.
    """

    reading = BackupReading(
        path="/media/BACKUP/persiaut-consulting/wordpress/",
        observed_at=datetime.now(timezone.utc),
    )

    assert reading.newest_file_mtime is None


def test_a_reading_may_carry_a_found_backup_file():

    observed_at = datetime.now(timezone.utc)
    newest = observed_at - timedelta(hours=1)

    reading = BackupReading(
        path="/media/BACKUP/persiaut-consulting/wordpress/",
        observed_at=observed_at,
        newest_file_mtime=newest,
    )

    assert reading.newest_file_mtime == newest


def test_a_newest_file_mtime_after_observed_at_is_refused():
    """
    A backup file cannot be newer than the moment it was observed —
    the same "the reading cannot contradict itself" discipline
    `StorageReading` already holds for used+free exceeding total.
    """

    observed_at = datetime.now(timezone.utc)
    future = observed_at + timedelta(hours=1)

    with pytest.raises(ValueError, match="newer"):
        BackupReading(
            path="/media/BACKUP/persiaut-consulting/wordpress/",
            observed_at=observed_at,
            newest_file_mtime=future,
        )


def test_a_newest_file_mtime_equal_to_observed_at_is_allowed():

    observed_at = datetime.now(timezone.utc)

    reading = BackupReading(
        path="/media/BACKUP/persiaut-consulting/wordpress/",
        observed_at=observed_at,
        newest_file_mtime=observed_at,
    )

    assert reading.newest_file_mtime == observed_at
