from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.backup_gap import MISSING, STALE, UNREACHABLE, BackupGap
from aistack.contracts.backup_reading import BackupReading
from aistack.contracts.backup_threshold import BackupThreshold


def find_backup_gaps(
    readings: Sequence[BackupReading],
    thresholds: Sequence[BackupThreshold],
) -> tuple[BackupGap, ...]:
    """
    Return the backup locations that fail their `OPS-0006` check: unreachable,
    no backup file found, or the newest file older than `max_age_hours`.

    A reading for a path with no declared threshold is skipped, not treated
    as healthy.
    """

    by_path = {threshold.path: threshold for threshold in thresholds}

    gaps: list[BackupGap] = []

    for reading in readings:
        threshold = by_path.get(reading.path)

        if threshold is None:
            continue

        if reading.unreachable:
            gaps.append(
                BackupGap(
                    reading=reading,
                    max_age_hours=threshold.max_age_hours,
                    reason=UNREACHABLE,
                )
            )
            continue

        if reading.newest_file_mtime is None:
            gaps.append(
                BackupGap(
                    reading=reading,
                    max_age_hours=threshold.max_age_hours,
                    reason=MISSING,
                )
            )
            continue

        age_hours = (
            reading.observed_at - reading.newest_file_mtime
        ).total_seconds() / 3600

        if age_hours > threshold.max_age_hours:
            gaps.append(
                BackupGap(
                    reading=reading,
                    max_age_hours=threshold.max_age_hours,
                    reason=STALE,
                )
            )

    return tuple(gaps)
