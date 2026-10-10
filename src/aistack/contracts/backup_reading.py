from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class BackupReading:
    """
    One backup directory at one point in time: whether any backup file
    was found under it, and how recent the newest one is.

    A reading, not a verdict: `aistack.runtime.backup_gap.find_backup_gaps`
    judges it against a declared threshold. `newest_file_mtime` is `None`
    when no file was found (directory absent or empty).
    """

    path: str
    observed_at: datetime
    newest_file_mtime: datetime | None = None
    # The error text when the path could not be read, else "". A disk
    # mounted on demand answers "No such device" while unmounted.
    unreachable: str = ""

    def __post_init__(self) -> None:
        if not self.path.strip():
            raise ValueError(
                "a backup reading is about one path; this one names none"
            )

        if self.unreachable and self.newest_file_mtime is not None:
            raise ValueError(
                f"{self.path} is reported unreachable ({self.unreachable}) "
                f"and yet with a newest backup file"
            )

        if (
            self.newest_file_mtime is not None
            and self.newest_file_mtime > self.observed_at
        ):
            raise ValueError(
                f"{self.path} reports a backup file newer "
                f"({self.newest_file_mtime.isoformat()}) than the moment "
                f"it was observed ({self.observed_at.isoformat()})"
            )
