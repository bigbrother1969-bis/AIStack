from __future__ import annotations

from collections.abc import Sequence

from aistack.contracts.backup_gap import MISSING, STALE, BackupGap
from aistack.contracts.backup_reading import BackupReading
from aistack.contracts.backup_threshold import BackupThreshold


def find_backup_gaps(
    readings: Sequence[BackupReading],
    thresholds: Sequence[BackupThreshold],
) -> tuple[BackupGap, ...]:
    """
    Which backup locations have failed the check `OPS-0006` declares
    for them: no backup file found at all, or the newest one found is
    older than the declared threshold allows.

    Mirrors `find_storage_shortage`: given readings already collected
    and thresholds already declared, decides which ones actually fail
    — it never proposes a threshold itself.

    A reading for a path with no declared threshold is silently not
    evaluated, not treated as healthy — the same "not measured is not
    zero" convention `find_storage_shortage` already holds for a
    mount `OPS-0005` has not been asked about yet.

    Pure: readings and thresholds already collected in, gaps out —
    the same discipline `find_storage_shortage` already holds.
    """

    by_path = {threshold.path: threshold for threshold in thresholds}

    gaps: list[BackupGap] = []

    for reading in readings:
        threshold = by_path.get(reading.path)

        if threshold is None:
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
