from __future__ import annotations

from dataclasses import dataclass

from aistack.contracts.backup_reading import BackupReading

# Closed set of reasons: the scope checks existence and freshness only
# (OPS-0006).
MISSING = "missing"
STALE = "stale"
# The declared path could not be read: neither missing nor stale is known.
UNREACHABLE = "unreachable"

REASONS = (MISSING, STALE, UNREACHABLE)


@dataclass(frozen=True)
class BackupGap:
    """
    A backup location that failed its OPS-0006 check: missing, stale or
    unreachable. The constructor checks the reason against the reading.

    `max_age_hours` is copied from the threshold that fired, so the gap
    states what fired then, not what the threshold says today.
    """

    reading: BackupReading
    max_age_hours: float
    reason: str

    def __post_init__(self) -> None:
        if self.reason not in REASONS:
            raise ValueError(
                f"{self.reading.path} cites {self.reason!r} as a backup "
                f"gap reason; only {REASONS} are detected in this scope "
                f"(existence and freshness only)"
            )

        if (self.reason == UNREACHABLE) != bool(self.reading.unreachable):
            raise ValueError(
                f"{self.reading.path}: a gap is 'unreachable' exactly when "
                f"its reading could not read the path"
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
