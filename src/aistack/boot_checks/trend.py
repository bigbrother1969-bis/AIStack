"""
How fast a disk fills (ADR-0032, slice O4): a robust line through what Beszel measured, said as days to full.

Beszel keeps the used space of each machine's system disk every 8 hours for about 27 days. The rate (GB per day)
is the median of the day-to-day growths over the last `window_days`: a copy or a restore that jumps the disk once or
twice is a step in two of those days, not a trend, and does not move the median, while a steady growth, even by daily
steps, does. A growth that comes only by a step a week is not seen as a rate (the percent limit of `systems` is what
catches it). The space left over that rate is the days to full. This is arithmetic, decided by the code: nothing here asks an engine, and a trend is only said when there
is enough history to carry one. Not enough history is *not measured*, never "fine".

What it does not see: only the system disk of a machine that Beszel watches. A data disk Beszel does not follow
is not in it, and the summary does not pretend otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

# Fewer points than this carry no line.
MIN_POINTS = 6
# The newest point must be younger than this, or the series is a past one (a machine that was silent).
FRESH = timedelta(days=2)
# A day's growth is read between a point and the one about a day before it, within this.
DAY_TOLERANCE = timedelta(hours=4)
# Beyond a year to full, a growth is not worth a line.
HORIZON_DAYS = 365.0


@dataclass(frozen=True)
class DiskPoint:
    at: datetime
    total: float
    used: float


@dataclass(frozen=True)
class Trend:
    """Where the disk stands (GB), how fast it grows (GB per day, negative when it empties) and the days left, if it grows."""

    used: float
    total: float
    rate: float
    days_to_full: float | None


def trend_of(points: tuple[DiskPoint, ...], now: datetime, window_days: int, min_days: int) -> Trend | None:
    """The trend over the last `window_days`, or `None` when the history cannot carry one."""

    window = sorted((point for point in points if now - point.at <= timedelta(days=window_days)), key=lambda point: point.at)

    if len(window) < MIN_POINTS:
        return None

    first, last = window[0], window[-1]

    if now - last.at > FRESH or last.at - first.at < timedelta(days=min_days) or last.total <= 0:
        return None

    slopes = []

    for later in window:
        near = [point for point in window if abs((later.at - point.at) - timedelta(days=1)) <= DAY_TOLERANCE]

        if near:
            earlier = min(near, key=lambda point: abs((later.at - point.at) - timedelta(days=1)))
            slopes.append((later.used - earlier.used) / ((later.at - earlier.at).total_seconds() / 86400))

    if not slopes:
        return None

    rate = median(slopes)
    left = max(last.total - last.used, 0.0)
    to_full = left / rate if rate > 0 else None

    return Trend(last.used, last.total, rate, to_full if to_full is not None and to_full <= HORIZON_DAYS else None)
