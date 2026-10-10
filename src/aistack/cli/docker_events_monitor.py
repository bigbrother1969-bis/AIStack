from __future__ import annotations

import json
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aistack.generators.collection_gap import record_collection_gap
from aistack.providers.docker.events import ExecNoiseFilter, collect_docker_events, enrich
from aistack.providers.docker.events_history import (
    DEFAULT_OUTPUT_PATH,
    record_docker_events,
)

# Same value as `aistack.timemachine.projection.docker_events.STEM`: the
# stream this monitor's gaps are filed under.
STREAM_STEM = "docker-events"

# Polling rather than a continuous `docker events` subscription; see
# `aistack.providers.docker.events` for why.
POLL_SECONDS = 10.0

# With no checkpoint, the first window looks back this far instead of
# being empty (`since == until`), so a manual `--once --dry-run` right
# after `docker restart` can see the events. Small and bounded: no full
# history backfill.
FIRST_RUN_LOOKBACK_SECONDS = 60.0

DEFAULT_CHECKPOINT_PATH = Path("reports/generated/docker-events/checkpoint.json")

# Root under which `record_collection_gap` writes.
DEFAULT_GENERATED_DIR = Path("reports/generated")

USAGE = (
    "usage: python -m aistack.cli.docker_events_monitor "
    "[--output PATH] [--checkpoint PATH] [--generated-dir PATH] "
    "[--once] [--dry-run]\n"
    "\n"
    "  Polls `docker events` since its own last checkpoint and\n"
    "  records every new event to Observation History.\n"
    "\n"
    "  --once        run a single poll/record cycle and exit,\n"
    "                instead of looping — for a first manual check\n"
    "                against the real Docker daemon.\n"
    "  --dry-run     print what would be recorded without writing\n"
    "                the history artifact or advancing the\n"
    "                checkpoint — unlike `resource_priority_monitor\n"
    "                --dry-run`, which still records its decision\n"
    "                history flagged `dry_run: true`: that monitor's\n"
    "                dry-run suppresses a mutating `docker update`\n"
    "                call this one has no equivalent of, so here the\n"
    "                closest side effect to suppress is persistence\n"
    "                itself — and, since R11, the same call this\n"
    "                flag already suppresses a second time.\n"
    "  --output      path to the events history artifact (default:\n"
    "                the real one this repository ships).\n"
    "  --checkpoint  path to the checkpoint file (default: the real\n"
    "                one this repository ships).\n"
    "  --generated-dir  root `record_collection_gap` (R11) writes\n"
    "                under (default: the real one this repository\n"
    "                ships) — independent of `--output`/`--checkpoint`\n"
    "                so a caller can redirect either without silently\n"
    "                redirecting the other.\n"
)


class _Stop(Exception):
    """Raised from the SIGTERM handler to unwind the loop cleanly."""


def parse(argv: list[str]) -> tuple[Path, Path, Path, bool, bool]:

    output_path = DEFAULT_OUTPUT_PATH
    checkpoint_path = DEFAULT_CHECKPOINT_PATH
    generated_dir = DEFAULT_GENERATED_DIR
    once = False
    dry_run = False
    rest = list(argv)

    while rest:
        argument = rest.pop(0)

        if argument in ("-h", "--help"):
            print(USAGE)
            raise SystemExit(0)

        if argument == "--output":
            if not rest:
                print("--output expects a path")
                raise SystemExit(2)
            output_path = Path(rest.pop(0))
            continue

        if argument == "--checkpoint":
            if not rest:
                print("--checkpoint expects a path")
                raise SystemExit(2)
            checkpoint_path = Path(rest.pop(0))
            continue

        if argument == "--generated-dir":
            if not rest:
                print("--generated-dir expects a path")
                raise SystemExit(2)
            generated_dir = Path(rest.pop(0))
            continue

        if argument == "--once":
            once = True
            continue

        if argument == "--dry-run":
            dry_run = True
            continue

        print(f"unrecognised argument: {argument}")
        raise SystemExit(2)

    return output_path, checkpoint_path, generated_dir, once, dry_run


def load_checkpoint(checkpoint_path: Path) -> str | None:
    """
    The `--since` boundary of the next poll, or None on a first run.

    An unreadable checkpoint counts as absent, so the monitor never
    crashes on a file it can re-establish.
    """

    try:
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    since = payload.get("since") if isinstance(payload, dict) else None
    return since if isinstance(since, str) else None


def save_checkpoint(checkpoint_path: Path, since: str) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(
        json.dumps({"since": since}, indent=2) + "\n", encoding="utf-8"
    )


def run_cycle(
    output_path: Path,
    checkpoint_path: Path,
    dry_run: bool,
    *,
    now: datetime | None = None,
    noise_filter: ExecNoiseFilter | None = None,
) -> list[dict[str, Any]]:
    """
    Collect every Docker event since the checkpoint, enrich and record them.

    On a first run the window starts `FIRST_RUN_LOOKBACK_SECONDS` before
    `until`. The checkpoint advances to `until`, not to the last event,
    so a quiet host does not poll an ever-widening window. Docker's
    `--since` is inclusive, so an event exactly on a boundary may be
    recorded twice; this is accepted.
    """

    when = now if now is not None else datetime.now(timezone.utc)
    checkpoint = load_checkpoint(checkpoint_path)
    since = checkpoint or (
        when - timedelta(seconds=FIRST_RUN_LOOKBACK_SECONDS)
    ).isoformat()
    until = when.isoformat()

    raw_events = collect_docker_events(since, until)
    # Drop exec noise (AIStack's package probes, healthchecks). A looping
    # caller passes one filter for its whole run, so a dropped exec's
    # `exec_die` is recognised in the next window too.
    noise_filter = noise_filter if noise_filter is not None else ExecNoiseFilter()
    events = [enrich(event) for event in raw_events if noise_filter.keep(event)]

    if not dry_run:
        record_docker_events(events, since=since, until=until, output_path=output_path)
        save_checkpoint(checkpoint_path, until)

    return events


def log_cycle(events: list[dict[str, Any]], label: str = "") -> None:
    """Print a line only when there are events or `label` is set, so empty cycles stay silent."""

    if not (events or label):
        return

    prefix = f"{label}: " if label else ""
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    subjects = sorted({str(event["subject"]) for event in events})

    print(f"{when} {prefix}new={len(events)} subjects={subjects}")


def main(argv: list[str] | None = None) -> None:

    # Line-buffer stdout: Python block-buffers a pipe, so lines would not
    # reach journald until the buffer fills.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    output_path, checkpoint_path, generated_dir, once, dry_run = parse(
        sys.argv[1:] if argv is None else argv
    )

    # ADR-0011 § 9 (R11): check for a gap before the first cycle, against
    # the checkpoint the previous run left. `--dry-run` skips it, as it
    # skips all persistence.
    if not dry_run:
        record_collection_gap(
            STREAM_STEM,
            checkpoint_until=load_checkpoint(checkpoint_path),
            now=datetime.now(timezone.utc),
            generated_dir=generated_dir,
        )

    def handle_sigterm(signum: int, frame: Any) -> None:
        raise _Stop()

    if not once:
        signal.signal(signal.SIGTERM, handle_sigterm)

    noise_filter = ExecNoiseFilter()

    try:
        while True:
            events = run_cycle(
                output_path, checkpoint_path, dry_run, noise_filter=noise_filter
            )

            # `--once` always prints, so a quiet manual check is not mistaken for no run.
            log_cycle(events, label="check" if once else "")

            if once:
                return

            time.sleep(POLL_SECONDS)

    except (KeyboardInterrupt, _Stop):
        log_cycle([], label="stopping")


if __name__ == "__main__":
    main()
