from datetime import datetime, timedelta, timezone

import pytest

from aistack.contracts.backup_gap import MISSING, STALE, BackupGap
from aistack.contracts.backup_reading import BackupReading

PATH = "/media/BACKUP/persiaut-consulting/wordpress/"


def missing_reading(observed_at: datetime | None = None) -> BackupReading:
    return BackupReading(
        path=PATH, observed_at=observed_at or datetime.now(timezone.utc)
    )


def stale_reading(age_hours: float) -> BackupReading:
    observed_at = datetime.now(timezone.utc)
    return BackupReading(
        path=PATH,
        observed_at=observed_at,
        newest_file_mtime=observed_at - timedelta(hours=age_hours),
    )


def test_a_gap_refuses_an_unknown_reason():

    with pytest.raises(ValueError, match=r"only .* are detected"):
        BackupGap(reading=missing_reading(), max_age_hours=168.0, reason="expired")


def test_missing_is_accepted_when_the_reading_has_no_backup_file():

    gap = BackupGap(reading=missing_reading(), max_age_hours=168.0, reason=MISSING)

    assert gap.reason == MISSING


def test_missing_is_refused_when_the_reading_does_report_a_backup_file():

    with pytest.raises(ValueError, match="cites 'missing'"):
        BackupGap(
            reading=stale_reading(age_hours=1), max_age_hours=168.0, reason=MISSING
        )


def test_stale_is_refused_when_the_reading_has_no_backup_file():
    """
    "No backup file found" is `MISSING`, never `STALE` — a `BackupGap`
    citing `STALE` states there is a file, only too old a one.
    """

    with pytest.raises(ValueError, match="that is 'missing', not 'stale'"):
        BackupGap(reading=missing_reading(), max_age_hours=168.0, reason=STALE)


def test_stale_is_refused_when_the_backup_is_within_threshold():

    with pytest.raises(ValueError, match="not what the threshold names"):
        BackupGap(
            reading=stale_reading(age_hours=100), max_age_hours=168.0, reason=STALE
        )


def test_stale_is_accepted_when_the_backup_is_older_than_threshold():

    gap = BackupGap(
        reading=stale_reading(age_hours=200), max_age_hours=168.0, reason=STALE
    )

    assert gap.reason == STALE


def test_stale_is_accepted_exactly_at_the_threshold_boundary():
    """
    Mirrors `find_storage_shortage`'s own "at or above" convention:
    the boundary itself is not yet a gap, only strictly past it — a
    `BackupGap` can only ever be constructed for what already crossed.
    """

    with pytest.raises(ValueError, match="not what the threshold names"):
        BackupGap(
            reading=stale_reading(age_hours=168.0), max_age_hours=168.0, reason=STALE
        )
