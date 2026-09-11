from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.backup_reading import BackupReading

# The two conditions this domain's v1 scope detects — closed the same
# way `ContainerDistress.REASONS` is: no third reason without a real
# case naming one (`GOV-P-001`). A path `OPS-0006` declares a
# threshold for is either missing its backup entirely, or has one
# that is older than the threshold allows — there is no third state
# in "existence and freshness only" (periodic restore tests and
# documentation currency are named out of scope, `OPS-0006` § *Out of
# scope*).
MISSING = "missing"
STALE = "stale"

REASONS = (MISSING, STALE)


@dataclass(frozen=True)
class BackupGap:
    """
    One backup location already found to have failed the check
    `OPS-0006` declares for it: no backup file found at all, or the
    newest one found is older than the declared threshold allows.

    Mirrors `StorageShortage`/`ContainerDistress`: the reading and the
    reason it was already found to fail, enforced here rather than
    only in the caller — `find_backup_gaps`
    (`aistack.runtime.backup_gap`) only ever constructs a `BackupGap`
    already confirmed to be one; it does not re-derive "missing or
    stale" from a bare reading handed to it from elsewhere.

    `max_age_hours` is copied from the `BackupThreshold` that fired,
    not re-looked-up later — the same "state what fired, not what
    fires today" `StorageShortage.threshold_value` already holds.
    """

    reading: BackupReading
    max_age_hours: float
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in REASONS:
            raise ValueError(
                f"{self.reading.path} cites {self.reason!r} as a backup "
                f"gap reason; only {REASONS} are detected in this scope "
                f"(existence and freshness only — the owner's chosen v1 "
                f"scope, 2026-09-11)"
            )

        if self.reason == MISSING and self.reading.newest_file_mtime is not None:
            raise ValueError(
                f"{self.reading.path} cites 'missing' but its own reading "
                f"reports a newest backup file at "
                f"{self.reading.newest_file_mtime.isoformat()}"
            )

        if self.reason == STALE:
            if self.reading.newest_file_mtime is None:
                raise ValueError(
                    f"{self.reading.path} cites 'stale' but its own "
                    f"reading reports no backup file found at all — that "
                    f"is 'missing', not 'stale'"
                )

            age_hours = (
                self.reading.observed_at - self.reading.newest_file_mtime
            ).total_seconds() / 3600

            if age_hours <= self.max_age_hours:
                raise ValueError(
                    f"{self.reading.path}'s newest backup is "
                    f"{age_hours:.1f} hours old, at or below its declared "
                    f"threshold of {self.max_age_hours:.1f} hours: this is "
                    f"not what the threshold names as stale"
                )
