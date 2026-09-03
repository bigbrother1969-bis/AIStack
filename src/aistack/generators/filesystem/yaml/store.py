from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from aistack.generators.filesystem.hardlink import MaterialisationReport


@dataclass(frozen=True)
class LastGeneration:
    """
    A `MaterialisationReport`, with the one fact it cannot know
    about itself: when it ran.

    `materialise_by_hardlink` is pure with respect to time — it
    reports what it did, not when. A POST answers the request that
    triggered it; the screen the owner opens afterwards has no
    request left to read that answer from. Decided 2026-09-03 for
    step 8: *the result of the last generation* is part of what
    the screen owes on every load, so it is saved beside the
    selection rather than carried only in a redirect's query
    string, which the next navigation discards.
    """

    report: MaterialisationReport
    generated_at: str


def save_last_generation_yaml(
    report: MaterialisationReport, path: Path
) -> Path:
    """Save a materialisation report as the last generation result."""

    generation = LastGeneration(
        report=report,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )

    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            asdict(generation), stream, sort_keys=False, allow_unicode=True
        )

    return path


def load_last_generation_yaml(path: Path) -> LastGeneration | None:
    """
    Load the last generation result, or `None` if the screen has
    never generated anything yet — a fact the screen must be able
    to say plainly, not paper over with zeros that would read as a
    generation that ran and changed nothing.
    """

    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(f"Last generation YAML must contain a mapping: {path}")

    return LastGeneration(
        report=_report_from(data.get("report", {})),
        generated_at=data.get("generated_at", ""),
    )


def _report_from(data: Any) -> MaterialisationReport:
    if not isinstance(data, dict):
        data = {}

    return MaterialisationReport(
        linked=tuple(data.get("linked") or ()),
        relinked=tuple(data.get("relinked") or ()),
        removed=tuple(data.get("removed") or ()),
        pruned=tuple(data.get("pruned") or ()),
        unchanged=int(data.get("unchanged") or 0),
        failed=tuple(tuple(pair) for pair in (data.get("failed") or ())),
        refused=data.get("refused") or "",
        dry_run=bool(data.get("dry_run") or False),
    )
