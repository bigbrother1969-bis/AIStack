"""
AIStack's data directory against its disk budget, and the compaction of
old observations (`ADR-0021`; the owner, 2026-10-09: a budget of 2 GB,
observations older than 90 days compressed, in place).

**Measured, never estimated.** `measure` walks the data directory and
adds up what is there; the pace is what was written over the last seven
days (file modification times), so the date the budget would be reached
is a projection from a measurement, said as such.

**Compressed, never deleted.** `compress_old` turns an observation file
older than the window into `<name>.gz` beside it, checks that the
compressed copy gives back exactly the same bytes, and only then
removes the plain file. `aistack.history` reads both the same way, so
the Time Machine rebuilds the same graph. The latest file of each
stream (the one beside `history/`) is never touched, nor anything
outside a `history/<stem>/` directory.
"""

from __future__ import annotations

import gzip
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from aistack.config import configured
from aistack.contracts.data_usage import DataUsageReading
from aistack.history.query import COMPRESSED_SUFFIX, _parse_history_filename

SHIPPED = Path(__file__).resolve().parent / "definitions" / "data_budget.yml"
MB = 1024 * 1024
LAST_COMPACTION = Path("data-budget") / "last-compaction"


@dataclass(frozen=True)
class DataBudget:
    budget_bytes: int
    warn_percent: int
    compress_after: timedelta
    compress: tuple[str, ...]


def load_data_budget(path: Path | None = None) -> DataBudget:
    source = path if path is not None else configured(SHIPPED)
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{source}: not a mapping")
    try:
        budget = DataBudget(
            budget_bytes=int(float(data["budget_mb"]) * MB),
            warn_percent=int(data.get("warn_percent", 80)),
            compress_after=timedelta(days=float(data.get("compress_after_days", 90))),
            compress=tuple(str(name) for name in data.get("compress") or ()),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{source}: {error}") from error
    if budget.budget_bytes <= 0 or not 0 < budget.warn_percent <= 100:
        raise ValueError(f"{source}: budget_mb must be positive, warn_percent between 1 and 100")
    return budget


def measure(generated_dir: Path, budget: DataBudget, now: datetime | None = None) -> DataUsageReading:
    moment = (now or datetime.now(timezone.utc)).timestamp()
    week_ago = moment - 7 * 86400
    total = 0
    files = 0
    recent = 0
    by_top: dict[str, int] = {}
    for root, _dirs, names in os.walk(generated_dir):
        top = Path(root).relative_to(generated_dir).parts
        key = top[0] if top else "."
        for name in names:
            try:
                info = os.stat(os.path.join(root, name), follow_symlinks=False)
            except OSError:
                continue
            total += info.st_size
            files += 1
            if top:
                by_top[key] = by_top.get(key, 0) + info.st_size
            else:
                by_top[name] = info.st_size
            if info.st_mtime >= week_ago:
                recent += info.st_size
    largest = tuple(sorted(by_top.items(), key=lambda item: item[1], reverse=True)[:6])
    return DataUsageReading(
        directory=str(generated_dir),
        used_bytes=total,
        budget_bytes=budget.budget_bytes,
        warn_percent=budget.warn_percent,
        files=files,
        daily_bytes=recent // 7 if files else None,
        largest=largest,
    )


@dataclass
class Compaction:
    files: int = 0
    before: int = 0
    after: int = 0
    problems: list[str] = field(default_factory=list)


def _old_observations(generated_dir: Path, budget: DataBudget, now: datetime) -> list[Path]:
    limit = now - budget.compress_after
    found = []
    for name in budget.compress:
        top = generated_dir / name
        if not top.is_dir():
            continue
        for root, _dirs, names in os.walk(top):
            parts = Path(root).parts
            # Only `…/history/<stem>/` directories.
            if len(parts) < 2 or parts[-2] != "history":
                continue
            for file_name in names:
                path = Path(root) / file_name
                if path.suffix == COMPRESSED_SUFFIX:
                    continue
                parsed = _parse_history_filename(path)
                if parsed is not None and parsed[0] < limit:
                    found.append(path)
    return sorted(found)


def compress_old(
    generated_dir: Path, budget: DataBudget, now: datetime | None = None, dry_run: bool = False
) -> Compaction:
    done = Compaction()
    for path in _old_observations(generated_dir, budget, now or datetime.now(timezone.utc)):
        target = path.with_name(path.name + COMPRESSED_SUFFIX)
        try:
            data = path.read_bytes()
            if dry_run:
                done.files += 1
                done.before += len(data)
                done.after += len(gzip.compress(data, compresslevel=6))
                continue
            if not target.exists():
                temporary = target.with_name(f".{target.name}.{os.getpid()}")
                with gzip.open(temporary, "wb", compresslevel=6) as stream:
                    stream.write(data)
                with gzip.open(temporary, "rb") as check:
                    if check.read() != data:
                        temporary.unlink(missing_ok=True)
                        done.problems.append(f"{path}: compressed copy differs, kept as it was")
                        continue
                os.utime(temporary, (path.stat().st_atime, path.stat().st_mtime))
                temporary.replace(target)
            else:
                # An earlier run was interrupted between the two steps.
                with gzip.open(target, "rb") as check:
                    if check.read() != data:
                        done.problems.append(f"{target}: differs from {path.name}, both kept")
                        continue
            path.unlink()
            done.files += 1
            done.before += len(data)
            done.after += target.stat().st_size
        except OSError as error:
            done.problems.append(f"{path}: {error}")
    return done


def compact_if_due(
    generated_dir: Path, budget: DataBudget, now: datetime | None = None, every: timedelta = timedelta(days=1)
) -> Compaction | None:
    """At most once per `every`: the vigil calls it at each pass."""

    moment = now or datetime.now(timezone.utc)
    stamp = generated_dir / LAST_COMPACTION
    try:
        last = datetime.fromisoformat(stamp.read_text(encoding="utf-8").strip())
        if moment - last < every:
            return None
    except (OSError, ValueError):
        pass
    done = compress_old(generated_dir, budget, moment)
    stamp.parent.mkdir(parents=True, exist_ok=True)
    stamp.write_text(moment.isoformat(timespec="seconds") + "\n", encoding="utf-8")
    return done


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024 or unit == "Go":
            return f"{size:.0f} {unit}" if unit == "o" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} Go"
