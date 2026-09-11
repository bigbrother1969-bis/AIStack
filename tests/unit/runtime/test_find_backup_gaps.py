from datetime import datetime, timedelta, timezone

from aistack.contracts.backup_gap import MISSING, STALE
from aistack.contracts.backup_reading import BackupReading
from aistack.contracts.backup_threshold import BackupThreshold
from aistack.runtime.backup_gap import find_backup_gaps

PATH = "/media/BACKUP/persiaut-consulting/wordpress/"


def missing_reading(path: str = PATH) -> BackupReading:
    return BackupReading(path=path, observed_at=datetime.now(timezone.utc))


def reading_aged(hours: float, path: str = PATH) -> BackupReading:
    observed_at = datetime.now(timezone.utc)
    return BackupReading(
        path=path,
        observed_at=observed_at,
        newest_file_mtime=observed_at - timedelta(hours=hours),
    )


def threshold(path: str = PATH, max_age_hours: float = 168.0) -> BackupThreshold:
    return BackupThreshold(path=path, max_age_hours=max_age_hours)


def test_a_missing_backup_is_flagged():

    gaps = find_backup_gaps([missing_reading()], [threshold()])

    assert len(gaps) == 1
    assert gaps[0].reason == MISSING


def test_a_fresh_backup_is_not_flagged():

    gaps = find_backup_gaps([reading_aged(1)], [threshold()])

    assert gaps == ()


def test_a_stale_backup_is_flagged():

    gaps = find_backup_gaps([reading_aged(200)], [threshold()])

    assert len(gaps) == 1
    assert gaps[0].reason == STALE


def test_exactly_at_the_threshold_is_not_flagged():
    """
    Mirrors `find_backup_gaps`'s own "strictly past" convention: the
    boundary itself is not yet stale.
    """

    gaps = find_backup_gaps([reading_aged(168.0)], [threshold(max_age_hours=168.0)])

    assert gaps == ()


def test_a_path_with_no_declared_threshold_is_silently_not_evaluated():

    gaps = find_backup_gaps([missing_reading(path="/undeclared/")], [])

    assert gaps == ()


def test_only_the_path_crossing_its_own_threshold_is_flagged_in_a_batch():

    fresh = reading_aged(1, path="/fresh/")
    stale = reading_aged(200, path="/stale/")

    gaps = find_backup_gaps(
        [fresh, stale],
        [threshold(path="/fresh/"), threshold(path="/stale/")],
    )

    assert [gap.reading.path for gap in gaps] == ["/stale/"]


def test_an_empty_reading_set_flags_nothing():

    assert find_backup_gaps([], [threshold()]) == ()
