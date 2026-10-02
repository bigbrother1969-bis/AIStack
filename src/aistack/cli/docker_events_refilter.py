"""
One-shot: move the `docker-events` history out of the stream into an
archive, then write back only what `ExecNoiseFilter` keeps.

Owner's decision, 2026-10-02 (`ADR-0011` § 27): the four days of
history recorded before the exec-noise filter existed — 34,488 files,
4.7 GB, 97 % `exec_*` from healthchecks and AIStack's own package
probes — are archived out of the stream, not deleted, and the stream is
rebuilt from that archive through the same filter the live monitor now
applies. The archive keeps every original byte; the history directory
`aistack.timemachine.projection.docker_events` reads afterwards holds
only the events a person could have caused, under each batch's own
original timestamp, so the graph rebuilt from it keeps each event's
real recording instant.

Run with the docker-events monitor stopped — it writes into the very
directory this moves — then rebuild the graph (`timemachine_rebuild`).
"""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.providers.docker.events import (
    ExecNoiseFilter,
    current_healthchecks_by_subject,
    docker_action_of,
)

DEFAULT_GENERATED_DIR = Path("reports/generated")
STEM = "docker-events"

USAGE = (
    "usage: python -m aistack.cli.docker_events_refilter "
    "[--generated-dir PATH] [--archive-name NAME] [--dry-run]\n"
    "\n"
    "  Moves reports/generated/docker-events/history/docker-events/ to\n"
    "  reports/generated/docker-events/archive/<NAME>/docker-events/,\n"
    "  then writes back, under each file's original name, only the\n"
    "  events the exec-noise filter keeps. Stop the docker-events\n"
    "  monitor first; rebuild the graph afterwards.\n"
    "\n"
    "  --dry-run       count what would be kept and dropped; move and\n"
    "                  write nothing.\n"
    "  --archive-name  archive directory name (default:\n"
    "                  unfiltered-<today, UTC>). Refused if it exists.\n"
    "  --generated-dir root to work under (default: the real one).\n"
)


@dataclass
class RefilterSummary:
    files_read: int = 0
    files_written: int = 0
    events_read: int = 0
    events_kept: int = 0
    dropped_by_action: Counter[str] = field(default_factory=Counter)


def parse(argv: list[str]) -> tuple[Path, str, bool]:
    generated_dir = DEFAULT_GENERATED_DIR
    archive_name = "unfiltered-" + datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dry_run = False
    rest = list(argv)

    while rest:
        argument = rest.pop(0)
        if argument in ("-h", "--help"):
            print(USAGE)
            raise SystemExit(0)
        if argument == "--generated-dir":
            if not rest:
                print("--generated-dir expects a path")
                raise SystemExit(2)
            generated_dir = Path(rest.pop(0))
            continue
        if argument == "--archive-name":
            if not rest:
                print("--archive-name expects a name")
                raise SystemExit(2)
            archive_name = rest.pop(0)
            continue
        if argument == "--dry-run":
            dry_run = True
            continue
        print(f"unrecognised argument: {argument}")
        raise SystemExit(2)

    return generated_dir, archive_name, dry_run


def _filter_batch(
    path: Path, noise_filter: ExecNoiseFilter, summary: RefilterSummary
) -> dict[str, Any] | None:
    """The batch with only its kept events, or `None` when none is kept or it cannot be read."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        return None

    summary.files_read += 1
    kept: list[Any] = []
    for event in events:
        summary.events_read += 1
        raw = event.get("raw") if isinstance(event, dict) else None
        if isinstance(raw, dict) and not noise_filter.keep(raw):
            summary.dropped_by_action[docker_action_of(raw).split(":", 1)[0]] += 1
            continue
        kept.append(event)

    summary.events_kept += len(kept)
    if not kept:
        return None
    return {**payload, "events": kept}


def refilter(
    generated_dir: Path,
    archive_name: str,
    dry_run: bool,
    *,
    noise_filter: ExecNoiseFilter | None = None,
) -> RefilterSummary:
    history_dir = generated_dir / STEM / "history" / STEM
    archive_dir = generated_dir / STEM / "archive" / archive_name / STEM

    if not history_dir.is_dir():
        raise SystemExit(f"no history to refilter at {history_dir}")
    if archive_dir.exists():
        raise SystemExit(f"archive already exists, refusing to overwrite: {archive_dir}")

    noise_filter = noise_filter or ExecNoiseFilter(
        healthchecks_by_subject=current_healthchecks_by_subject(),
        remember_uninspectable=True,
    )
    summary = RefilterSummary()

    if dry_run:
        source_dir = history_dir
    else:
        archive_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(history_dir), str(archive_dir))
        history_dir.mkdir(parents=True, exist_ok=True)
        source_dir = archive_dir

    for path in sorted(source_dir.iterdir()):
        if not path.is_file() or path.suffix != ".json":
            continue
        batch = _filter_batch(path, noise_filter, summary)
        if batch is None or dry_run:
            continue
        (history_dir / path.name).write_text(
            json.dumps(batch, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        summary.files_written += 1

    return summary


def report(summary: RefilterSummary, dry_run: bool) -> None:
    mode = "dry-run" if dry_run else "done"
    print(
        f"{mode}: files read={summary.files_read} "
        f"{'would keep' if dry_run else 'written'}="
        f"{summary.files_written if not dry_run else '-'} "
        f"events read={summary.events_read} kept={summary.events_kept} "
        f"dropped={summary.events_read - summary.events_kept}"
    )
    for action, count in summary.dropped_by_action.most_common():
        print(f"  dropped {count:8d}  {action}")


def main(argv: list[str] | None = None) -> None:
    generated_dir, archive_name, dry_run = parse(sys.argv[1:] if argv is None else argv)
    summary = refilter(generated_dir, archive_name, dry_run)
    report(summary, dry_run)


if __name__ == "__main__":
    main()
