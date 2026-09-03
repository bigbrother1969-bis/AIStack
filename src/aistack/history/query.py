from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


# The one true filename format Observation History writes in
# (`generators/history.py`'s `write_artifact_with_history`):
# `<%Y-%m-%dT%H-%M-%SZ>[-<suffix>]<ext>`. isoformat is not used
# because a filesystem path cannot carry the `:` it contains — see
# that function's docstring. This module is the read side of the
# same contract, so it parses exactly what that function writes
# and nothing looser.
_FILENAME_STAMP = re.compile(
    r"^(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)(?:-(?P<suffix>\d+))?$"
)
_STAMP_FORMAT = "%Y-%m-%dT%H-%M-%SZ"


@dataclass(frozen=True)
class HistoricalObservation:
    """
    One artifact as it stood at a moment in the past — the unit
    the query layer hands back, one `stem`/`observed_at` pair
    resolved to the file that actually holds that content.
    """

    stem: str
    observed_at: datetime
    path: Path

    def read(self) -> str:
        return self.path.read_text(encoding="utf-8")


def format_instant(instant: datetime) -> str:
    """The one filename-safe rendering of an instant, shared by writer and reader."""

    return instant.astimezone(timezone.utc).strftime(_STAMP_FORMAT)


def parse_instant(text: str) -> datetime:
    """
    Parse a `format_instant`-shaped string back into a UTC
    datetime. Raises `ValueError` naming the expected shape on
    anything else, rather than a bare parser error — this is
    meant to be typed at a terminal from what `list_instants`
    or a directory listing just printed.
    """

    try:
        return datetime.strptime(text, _STAMP_FORMAT).replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(
            f"{text!r} is not an instant in the "
            f"{_STAMP_FORMAT!r} shape (e.g. 2026-09-03T18-05-00Z)"
        ) from exc


def _history_dir(generated_dir: Path, stem: str) -> Path:
    return generated_dir / "history" / stem


def _parse_history_filename(path: Path) -> tuple[datetime, int] | None:
    """
    The instant a history file was written, and its collision
    rank (0 for the unsuffixed file, the suffix number otherwise).
    `None` for anything in the directory that isn't one of this
    module's own files.
    """

    match = _FILENAME_STAMP.match(path.stem)
    if match is None:
        return None

    instant = datetime.strptime(match.group("stamp"), _STAMP_FORMAT).replace(
        tzinfo=timezone.utc
    )
    suffix = int(match.group("suffix")) if match.group("suffix") else 0
    return instant, suffix


def available_stems(generated_dir: Path) -> list[str]:
    """
    Every artifact kind that has Observation History under
    `generated_dir` — the `history/<stem>/` subdirectories
    `write_artifact_with_history` creates, one per artifact kind.
    """

    history_root = generated_dir / "history"
    if not history_root.is_dir():
        return []

    return sorted(child.name for child in history_root.iterdir() if child.is_dir())


def available_instants(generated_dir: Path, stem: str) -> list[datetime]:
    """
    Every instant at which `stem` was observed, oldest first.

    Two writes landing in the same wall-clock second collapse to
    one instant here: `write_artifact_with_history`'s collision
    suffix exists to keep both files on disk, not to make them two
    distinct historical moments — `observation_at` is what picks
    between them.
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
    What `stem` looked like at `at`: the most recent observation
    at or before that instant. `None` when no such observation
    exists — `at` predates the first one, or `stem` has no history
    at all.

    A naive `at` is treated as UTC, matching the convention every
    instant in this history is already recorded in
    (`datetime.now(timezone.utc)`, per `generators/history.py`).

    When several writes land in the same wall-clock second, the
    last one written is what was actually current at that instant:
    ties are broken by the collision suffix, highest wins.
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
