"""
How fast a disk fills (ADR-0032, slice O4): a straight line through what Beszel measured, said as days to full.

Beszel keeps the used space of each machine's system disk every 8 hours for about 27 days. A line fitted
through the last `window_days` of it gives a rate in GB per day; the space left over that rate is the days to
full. This is arithmetic, decided by the code: nothing here asks an engine, and a trend is only said when there
is enough history to carry one. Not enough history is *not measured*, never "fine".

What it does not see: only the system disk of a machine that Beszel watches. A data disk Beszel does not follow
is not in it, and the summary does not pretend otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# Fewer points than this carry no line.
MIN_POINTS = 6
# The newest point must be younger than this, or the series is a past one (a machine that was silent).
FRESH = timedelta(days=2)
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

    days = [(point.at - first.at).total_seconds() / 86400 for point in window]
    mean_t = sum(days) / len(days)
    mean_u = sum(point.used for point in window) / len(window)
    spread = sum((t - mean_t) ** 2 for t in days)

    if spread == 0:
        return None

    rate = sum((t - mean_t) * (point.used - mean_u) for t, point in zip(days, window, strict=True)) / spread
    left = max(last.total - last.used, 0.0)
    to_full = left / rate if rate > 0 else None

    return Trend(last.used, last.total, rate, to_full if to_full is not None and to_full <= HORIZON_DAYS else None)
