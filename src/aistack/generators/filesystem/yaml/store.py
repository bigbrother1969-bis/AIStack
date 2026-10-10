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
    A `MaterialisationReport` with the time it ran.

    Saved beside the selection so the screen can show the last
    generation's result on every load, not only in the redirect that
    follows the POST.
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
    Load the last generation result, or `None` if nothing was ever
    generated (distinct from a generation that changed nothing).
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
