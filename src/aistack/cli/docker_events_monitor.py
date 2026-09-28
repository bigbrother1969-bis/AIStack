from __future__ import annotations

import json
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from aistack.providers.docker.events import collect_docker_events, enrich
from aistack.providers.docker.events_history import (
    DEFAULT_OUTPUT_PATH,
    record_docker_events,
)

# Cadrage 2026-09-28 (`go 1.5`): a governed polling loop, the same
# shape `aistack.cli.resource_priority_monitor` already established
# as this heritage's one precedent for a long-running collector — see
# `aistack.providers.docker.events`'s own module comment for the full
# reasoning the owner chose this over a continuous `docker events`
# subscription.
#
# Docker events are less time-sensitive than the CPU/Jellyfin
# transitions `resource_priority_monitor`'s own `POLL_SECONDS = 5.0`
# watches (a missed 5-second window there can mean a throttled
# container during real playback); nothing here is watching for a
# human-perceptible transition. Proposed at double that interval — the
# agent's own default, not tuned against a real measurement, and the
# owner's to change with a single edit here, the same way
# `resource_priority_monitor.py`'s own comment already names its
# constant as "the owner's own decision... not tuned here".
POLL_SECONDS = 10.0

# Found needed 2026-09-28, the day this monitor was first run by hand on
# GIGABYTE: `./run_docker_events_monitor.sh --once --dry-run`, its own
# `USAGE` text's stated purpose ("for a first manual check against the
# real Docker daemon"), printed nothing at all — not an error, silence.
# A first run with no checkpoint set `since = until = now()`, a
# zero-width window that structurally cannot observe anything Docker has
# ever reported, however real; `--dry-run` compounds it, since it never
# persists a checkpoint either, so a *second* `--once --dry-run` right
# after computes its own fresh "now" and is exactly as empty as the
# first — two manual checks can never build on each other.
#
# `run_cycle`'s own first-run default now looks back this many seconds
# instead of starting at `until` — small and bounded, not the unmeasured
# backfill `ARC-P-006` warns this module's own docstring against; long
# enough that `docker restart <container>` followed immediately by
# `--once --dry-run` has a real chance of being seen, on GIGABYTE's own
# 5-second `POLL_SECONDS`-adjacent order of magnitude. Applies to every
# first run, looping or `--once` alike — a service started fresh, or
# restarted after a crash, is no worse off catching the few seconds
# before its own start than losing them outright.
FIRST_RUN_LOOKBACK_SECONDS = 60.0

DEFAULT_CHECKPOINT_PATH = Path("reports/generated/docker-events/checkpoint.json")

USAGE = (
    "usage: python -m aistack.cli.docker_events_monitor "
    "[--output PATH] [--checkpoint PATH] [--once] [--dry-run]\n"
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
    "                itself.\n"
    "  --output      path to the events history artifact (default:\n"
    "                the real one this repository ships).\n"
    "  --checkpoint  path to the checkpoint file (default: the real\n"
    "                one this repository ships).\n"
)


class _Stop(Exception):
    """Raised from the SIGTERM handler to unwind the loop cleanly."""


def parse(argv: list[str]) -> tuple[Path, Path, bool, bool]:

    output_path = DEFAULT_OUTPUT_PATH
    checkpoint_path = DEFAULT_CHECKPOINT_PATH
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

        if argument == "--once":
            once = True
            continue

        if argument == "--dry-run":
            dry_run = True
            continue

        print(f"unrecognised argument: {argument}")
        raise SystemExit(2)

    return output_path, checkpoint_path, once, dry_run


def load_checkpoint(checkpoint_path: Path) -> str | None:
    """
    The `--since` boundary of the next poll, or `None` on a first run
    — no checkpoint file yet, or one that fails to parse (treated the
    same as absent: a monitor must never crash for good on a
    corrupted checkpoint it can simply re-establish).
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
) -> list[dict[str, Any]]:
    """
    One poll: read the checkpoint (or, on a first run, default to
    `FIRST_RUN_LOOKBACK_SECONDS` before `until` — a small, bounded
    lookback, not the unmeasured full-history backfill `ARC-P-006`
    warns against, but enough for a manual `--once --dry-run` check to
    actually have a chance of observing something real; see that
    constant's own comment for the incident that found this needed),
    collect every event since then, enrich, and record.

    **The checkpoint advances to `until`, not to the last event's own
    `occurred_at`.** A cycle observing zero events must still move the
    window forward — otherwise a quiet host would poll the same
    ever-widening `[since, now)` range forever. This accepts one known,
    documented edge: an event landing exactly on a previous `until`
    boundary could in principle be seen twice, across two consecutive
    cycles' `--since`/`--until` windows both including that instant.
    Docker's own `--since` is inclusive; deduplicating that instant
    would need a same-instant identity beyond what a real event
    carries. Left as a stated trade-off, not solved for a duplicate
    this project has not yet observed in practice (`ARC-P-006`).
    """

    when = now if now is not None else datetime.now(timezone.utc)
    checkpoint = load_checkpoint(checkpoint_path)
    since = checkpoint or (
        when - timedelta(seconds=FIRST_RUN_LOOKBACK_SECONDS)
    ).isoformat()
    until = when.isoformat()

    raw_events = collect_docker_events(since, until)
    events = [enrich(event) for event in raw_events]

    if not dry_run:
        record_docker_events(events, since=since, until=until, output_path=output_path)
        save_checkpoint(checkpoint_path, until)

    return events


def log_cycle(events: list[dict[str, Any]], label: str = "") -> None:
    """
    Printed only when there is something to read — `resource_priority
    _monitor.log_cycle`'s own reasoning: a monitor polling every
    `POLL_SECONDS` that logged every empty cycle would bury the one
    line that matters.
    """

    if not (events or label):
        return

    prefix = f"{label}: " if label else ""
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    subjects = sorted({str(event["subject"]) for event in events})

    print(f"{when} {prefix}new={len(events)} subjects={subjects}")


def main(argv: list[str] | None = None) -> None:

    # Line-buffer stdout under systemd — the exact defect
    # `resource_priority_monitor.main`'s own comment documents and
    # fixes the same way: a journal line that had already run,
    # invisible in `journalctl` because Python block-buffers a pipe by
    # default.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    output_path, checkpoint_path, once, dry_run = parse(
        sys.argv[1:] if argv is None else argv
    )

    def handle_sigterm(signum: int, frame: Any) -> None:
        raise _Stop()

    if not once:
        signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        while True:
            events = run_cycle(output_path, checkpoint_path, dry_run)

            # `--once` always prints — the same incident
            # `FIRST_RUN_LOOKBACK_SECONDS`'s own comment names: a manual
            # check that stays silent on an empty cycle looks
            # indistinguishable from one that never ran at all. The
            # loop keeps `log_cycle`'s own "silent unless something"
            # discipline unchanged — a service polling every
            # `POLL_SECONDS` for days must not flood the journal with a
            # line for every empty cycle.
            log_cycle(events, label="check" if once else "")

            if once:
                return

            time.sleep(POLL_SECONDS)

    except (KeyboardInterrupt, _Stop):
        log_cycle([], label="stopping")


if __name__ == "__main__":
    main()
