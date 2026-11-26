"""
The data disks of the host and how fast they fill (ADR-0032, slice O4b).

The mounts the host shows to the service are read the way Settings reads them (`/proc/self/mounts` and `statvfs`,
never a command). Without a declaration, what is mounted under `/media` or `/mnt` is a data disk; the system disk is
Beszel's (O4). One sample per disk is kept about every 7 hours in a small journal, so the trend of `trend.py` has
something to fit: the journal is what the service keeps for itself, written by `state.py` like the verdict.

Space is the space an ordinary program can write: what ext4 keeps in reserve counts as used, so the percent is the
one `df` shows, give or take a point.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from aistack.boot_checks.trend import DiskPoint
from aistack.host.mounts import MountRow, Usage, disks_and_mounts, read_proc_mounts
from aistack.host.mounts import _statvfs as statvfs

USAGE = "usage-history.jsonl"
GB = 1024**3
# A new sample of a disk is kept when the last one is at least this old.
SAMPLE_EVERY = timedelta(hours=7)
# Without a declaration, a data disk is mounted under one of these.
AUTOMATIC = ("/media/", "/mnt/")
MAX_LINES = 20000


@dataclass(frozen=True)
class Sample:
    """The used and total space of one disk (GB) at one moment."""

    at: datetime
    point: str
    total: float
    used: float


@dataclass(frozen=True)
class UsageReading:
    """The disks as they are now and the series kept for each, oldest first."""

    samples: tuple[Sample, ...] = ()
    history: tuple[tuple[str, tuple[DiskPoint, ...]], ...] = field(default_factory=tuple)


def read_samples(
    declared: tuple[str, ...],
    now: datetime,
    read: Callable[[], str] = read_proc_mounts,
    measure: Callable[[str], Usage] = statvfs,
    is_file: Callable[[str], bool] = os.path.isfile,
) -> tuple[Sample, ...]:
    """The data disks now: the declared mount points, or everything under `/media` and `/mnt`; one per device."""

    rows: list[MountRow] = disks_and_mounts({}, read, measure, is_file)
    seen: set[str] = set()
    found = []

    for row in rows:
        point = row.mount.point
        wanted = point in declared if declared else point.startswith(AUTOMATIC)

        if not wanted or row.usage is None or row.usage.total <= 0 or row.mount.device in seen:
            continue

        seen.add(row.mount.device)
        found.append(Sample(now, point, round(row.usage.total / GB, 2), round((row.usage.total - row.usage.free) / GB, 2)))

    return tuple(sorted(found, key=lambda sample: sample.point))


def parse(text: str) -> list[Sample]:
    """The samples of a journal text; a line that is not one is left out."""

    found = []

    for line in text.splitlines():
        try:
            raw = json.loads(line)
            moment = datetime.fromisoformat(str(raw["at"]))
            total, used, point = float(raw["total"]), float(raw["used"]), str(raw["point"])
        except (ValueError, KeyError, TypeError):
            continue

        found.append(Sample(moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc), point, total, used))

    return found


def due(kept: list[Sample], current: tuple[Sample, ...], now: datetime) -> list[Sample]:
    """The current samples whose disk has none newer than `SAMPLE_EVERY`."""

    last: dict[str, datetime] = {}

    for sample in kept:
        last[sample.point] = max(last.get(sample.point, sample.at), sample.at)

    return [sample for sample in current if sample.point not in last or now - last[sample.point] >= SAMPLE_EVERY]


def prune(samples: list[Sample], now: datetime, days: int) -> list[Sample]:
    """What is younger than `days`, the newest `MAX_LINES` at most, oldest first."""

    young = sorted((sample for sample in samples if now - sample.at <= timedelta(days=days)), key=lambda sample: sample.at)

    return young[-MAX_LINES:]


def series(samples: list[Sample]) -> tuple[tuple[str, tuple[DiskPoint, ...]], ...]:
    """The samples as one series per disk."""

    by_point: dict[str, list[DiskPoint]] = {}

    for sample in sorted(samples, key=lambda item: item.at):
        by_point.setdefault(sample.point, []).append(DiskPoint(sample.at, sample.total, sample.used))

    return tuple((point, tuple(points)) for point, points in sorted(by_point.items()))


def read_history(directory: Path) -> list[Sample]:
    try:
        return parse((directory / USAGE).read_text(encoding="utf-8"))
    except OSError:
        return []
