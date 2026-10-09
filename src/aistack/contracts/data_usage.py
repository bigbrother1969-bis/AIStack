"""
What AIStack's data directory takes on its disk, against its declared
budget (`ADR-0021`, 2026-10-09).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DataUsageReading:
    directory: str
    used_bytes: int
    budget_bytes: int
    warn_percent: int
    files: int
    # What was written over the last seven days, a day on average;
    # None when nothing could say it.
    daily_bytes: int | None = None
    # The biggest directories, (name, bytes), largest first.
    largest: tuple[tuple[str, int], ...] = ()

    def __post_init__(self) -> None:
        if self.budget_bytes <= 0:
            raise ValueError("a data budget is a positive size")
        if not 0 < self.warn_percent <= 100:
            raise ValueError("warn_percent is between 1 and 100")

    @property
    def percent(self) -> int:
        return int(self.used_bytes * 100 // self.budget_bytes)

    @property
    def days_left(self) -> int | None:
        """Days until the budget is reached at the recent pace."""

        if not self.daily_bytes or self.used_bytes >= self.budget_bytes:
            return None
        return int((self.budget_bytes - self.used_bytes) // self.daily_bytes)
