from __future__ import annotations

import gzip

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


# The filename format `write_artifact_with_history` writes:
# `<%Y-%m-%dT%H-%M-%SZ>[-<suffix>]<ext>` (no `:`, which isoformat would
# put in a path). Parsed strictly, nothing looser.
_FILENAME_STAMP = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)(?:-(?P<suffix>\d+))?$"
)
_STAMP_FORMAT = "%Y-%m-%dT%H-%M-%SZ"
COMPRESSED_SUFFIX = ".gz"


@dataclass(frozen=True)
class HistoricalObservation:
    """One artifact as it stood at a past instant, and the file holding it."""

    stem: str
    observed_at: datetime
    path: Path
    # The collision suffix `write_artifact_with_history` gave the file:
    # 0 for the first write of a second, 1, 2… for the next ones.
    rank: int = 0

    @property
    def label(self) -> str:
        """The file name without extension: `format_instant`, plus
        `-<rank>` for a later write in the same second."""

        stamp = format_instant(self.observed_at)
        return f"{stamp}-{self.rank}" if self.rank else stamp

    def read(self) -> str:
        # Observations older than the data budget's window are kept
        # gzip-compressed, never deleted (ADR-0021).
        if self.path.suffix == COMPRESSED_SUFFIX:
            with gzip.open(self.path, "rt", encoding="utf-8") as stream:
                return stream.read()
        return self.path.read_text(encoding="utf-8")


def format_instant(instant: datetime) -> str:
    """The one filename-safe rendering of an instant, shared by writer and reader."""

    return instant.astimezone(timezone.utc).strftime(_STAMP_FORMAT)


def parse_instant(text: str) -> datetime:
    """
    Parse a `format_instant`-shaped string into a UTC datetime. Raises
    `ValueError` naming the expected shape otherwise.
    """

    try:
        return datetime.strptime(text, _STAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(
            f"{text!r} is not an instant in the "
            f"{_STAMP_FORMAT!r} shape (e.g. 2026-09-03T18-05-00Z)"
        ) from exc


def latest_observations(generated_dir: Path, stem: str) -> list[HistoricalObservation]:
    """
    Every instant `stem` was observed at, oldest first, each with the
    observation current at that instant.

    Same result as calling `observation_at` for each of
    `available_instants`, but in one directory scan: the per-instant
    form is quadratic and too slow on large histories.
    """

    best: dict[datetime, tuple[int, Path]] = {}
    for path in _history_dir(generated_dir, stem).glob("*"):
        parsed = _parse_history_filename(path)
        if parsed is None:
            continue
        instant, rank = parsed
        current = best.get(instant)
        if current is None or rank > current[0]:
            best[instant] = (rank, path)

    return [
        HistoricalObservation(stem=stem, observed_at=instant, path=best[instant][1])
        for instant in sorted(best)
    ]


def every_version(generated_dir: Path, stem: str) -> list[HistoricalObservation]:
    """
    Every file `stem`'s history holds, oldest first, including several
    written in the same second, in write order.

    Unlike `latest_observations`, which keeps only the last write of a
    second, this suits histories whose files are versions rather than
    snapshots.
    """

    found: list[HistoricalObservation] = []
    for path in _history_dir(generated_dir, stem).glob("*"):
        parsed = _parse_history_filename(path)
        if parsed is None:
            continue
        instant, rank = parsed
        found.append(HistoricalObservation(stem=stem, observed_at=instant, path=path, rank=rank))
    return sorted(found, key=lambda observation: (observation.observed_at, observation.rank))


def _history_dir(generated_dir: Path, stem: str) -> Path:
    return generated_dir / "history" / stem


def _parse_history_filename(path: Path) -> tuple[datetime, int] | None:
    """
    The instant a history file was written, and its collision rank (0
    for the unsuffixed file). `None` for any other file.
    """

    # `<stamp>.json.gz` (ADR-0021) has the same instant and rank as the
    # `<stamp>.json` it was.
    name = Path(path.stem) if path.suffix == COMPRESSED_SUFFIX else path
    match = _FILENAME_STAMP.match(name.stem)
    if match is None:
        return None

    instant = datetime.strptime(match.group("stamp"), _STAMP_FORMAT).replace(
        tzinfo=timezone.utc
    )
    suffix = int(match.group("suffix")) if match.group("suffix") else 0
    return instant, suffix


def available_stems(generated_dir: Path) -> list[str]:
    """
    Every artifact kind with history under `generated_dir`: the
    `history/<stem>/` subdirectories.
    """

    history_root = generated_dir / "history"
    if not history_root.is_dir():
        return []

    return sorted(child.name for child in history_root.iterdir() if child.is_dir())


def available_instants(generated_dir: Path, stem: str) -> list[datetime]:
    """
    Every instant at which `stem` was observed, oldest first. Writes in
    the same second count as one instant.
    """

    instants: set[datetime] = set()
    for path in _history_dir(generated_dir, stem).glob("*"):
        parsed = _parse_history_filename(path)
        if parsed is not None:
            instants.add(parsed[0])

    return sorted(instants)


def observation_at(
    generated_dir: Path, stem: str, at: datetime
) -> HistoricalObservation | None:
    """
    What `stem` looked like at `at`: the most recent observation at or
    before that instant, or `None`.

    A naive `at` is treated as UTC. Among writes in the same second, the
    highest collision suffix (the last written) wins.
    """

    if at.tzinfo is None:
        at = at.replace(tzinfo=timezone.utc)

    best: tuple[datetime, int, Path] | None = None
    for path in _history_dir(generated_dir, stem).glob("*"):
        parsed = _parse_history_filename(path)
        if parsed is None:
            continue

        instant, rank = parsed
        if instant > at:
            continue

        candidate = (instant, rank, path)
        if best is None or candidate[:2] > best[:2]:
            best = candidate

    if best is None:
        return None

    instant, _rank, path = best
    return HistoricalObservation(stem=stem, observed_at=instant, path=path)
