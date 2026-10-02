from __future__ import annotations

import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.generators.collection_gap import record_collection_gap
from aistack.providers.docker.diff import collect_running_container_diffs
from aistack.providers.docker.diff_history import (
    DEFAULT_GENERATED_DIR,
    has_changed,
    record_docker_diff,
)

# `aistack.timemachine.projection.docker_diff.STREAM_STEM` redeclared
# here — the same cross-boundary convention `aistack.cli
# .docker_events_monitor.STREAM_STEM`'s own comment already names.
STREAM_STEM = "docker-diff"

# Cadrage 2026-09-28 (`go 1.5`, second collector): the same governed
# polling loop `aistack.cli.docker_events_monitor` already established
# for the first one — see that module's own comment for the full
# reasoning against a continuous subscription (which `docker diff`
# has no equivalent of in any case: it is a point-in-time snapshot
# command, not a stream).
#
# Not tuned against a real measurement — the owner's own decision to
# change with a single edit here, the same restraint
# `docker_events_monitor.POLL_SECONDS`'s own comment already states:
# a container's filesystem drifting under active use is not more
# time-sensitive than a Docker event.
#
# **Tuned 2026-10-02, against a real measurement this time.** At 10 s,
# one `docker diff` per running container (~59 on the reference host)
# kept `dockerd` above 100 % CPU permanently, for a stream that
# recorded 1,760 changed snapshots in five days. Owner's cadrage: every
# 15 minutes — a filesystem drifting under use is not urgent to the
# second. A monitor restart still takes a first pass immediately.
POLL_SECONDS = 900.0

DEFAULT_CHECKPOINT_PATH = Path("reports/generated/docker-diff/checkpoint.json")

USAGE = (
    "usage: python -m aistack.cli.docker_diff_monitor "
    "[--checkpoint PATH] [--generated-dir PATH] [--once] [--dry-run]\n"
    "\n"
    "  Polls every running container's own `docker diff` every 15 min\n"
    "  (filtered against that container's own declared mounts) and\n"
    "  records a subject's own snapshot to Observation History only\n"
    "  when it differs from what was last recorded for it.\n"
    "\n"
    "  --once        run a single poll/record cycle and exit,\n"
    "                instead of looping — for a first manual check\n"
    "                against the real Docker daemon.\n"
    "  --dry-run     print which subjects would be recorded without\n"
    "                writing anything or advancing the checkpoint —\n"
    "                the same distinction `docker_events_monitor\n"
    "                --dry-run` already draws for its own stream.\n"
    "  --checkpoint  path to this monitor's own R11 checkpoint file,\n"
    "                which only ever records when this process's own\n"
    "                cycles last ran (default: the real one this\n"
    "                repository ships) — unrelated to the per-subject\n"
    "                `docker-diff.json` write-on-change comparison,\n"
    "                which reads each subject's own stable \"latest\"\n"
    "                file instead (`aistack.providers.docker\n"
    "                .diff_history.has_changed`).\n"
    "  --generated-dir  root both `record_collection_gap` (R11) and\n"
    "                every per-subject snapshot are written under\n"
    "                (default: the real one this repository ships).\n"
)


class _Stop(Exception):
    """Raised from the SIGTERM handler to unwind the loop cleanly."""


def parse(argv: list[str]) -> tuple[Path, Path, bool, bool]:

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

    return checkpoint_path, generated_dir, once, dry_run


def load_checkpoint(checkpoint_path: Path) -> str | None:
    """
    The instant this monitor's own last cycle actually ran, or `None`
    on a first run — no checkpoint file yet, or one that fails to
    parse (treated the same as absent, the same defensive posture
    `docker_events_monitor.load_checkpoint` already holds).

    **Not the same thing `docker_events_monitor`'s own checkpoint
    is.** That one is a query boundary (`--since`, the start of the
    next poll window); this monitor polls current state each cycle,
    with no window to bound — this checkpoint exists solely so R11
    (`record_collection_gap`) has a "last known coverage" instant to
    measure a restart against.
    """

    try:
        payload = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    last_run = payload.get("last_run") if isinstance(payload, dict) else None
    return last_run if isinstance(last_run, str) else None


def save_checkpoint(checkpoint_path: Path, last_run: str) -> None:
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    checkpoint_path.write_text(
        json.dumps({"last_run": last_run}, indent=2) + "\n", encoding="utf-8"
    )


def run_cycle(
    generated_dir: Path,
    checkpoint_path: Path,
    dry_run: bool,
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    One poll: every running container's current `docker diff`
    (`aistack.providers.docker.diff.collect_running_container_diffs`
    — decisions 1-2 of that module's own comment already applied),
    recorded per subject only where it actually changed.

    **The checkpoint advances every non-dry-run cycle, whether or not
    anything changed** — the same reasoning
    `docker_events_monitor.run_cycle`'s own docstring gives for its
    checkpoint always advancing to `until`: a quiet cycle, with every
    container's diff unchanged, must still move this monitor's own
    "last known coverage" forward, or a later restart's R11 gap-check
    would measure from stale, arbitrarily old state instead of from
    when this process was actually still running and actually still
    looking.

    Returns one entry per subject that actually changed this cycle
    (`{"subject", "changes"}`, `changes` the count, not the list
    itself — `log_cycle`'s own concern, kept small) — in both dry-run
    and normal mode, so a manual `--once --dry-run` check reports
    exactly what a real run would have recorded, without writing
    anything itself.
    """

    when = now if now is not None else datetime.now(timezone.utc)
    diffs = collect_running_container_diffs()

    changed: list[dict[str, Any]] = []
    for entry in diffs:
        subject = entry["subject"]
        entry_changes = entry["changes"]

        if dry_run:
            is_new = has_changed(subject, entry_changes, generated_dir=generated_dir)
        else:
            is_new = (
                record_docker_diff(
                    subject, entry_changes, generated_dir=generated_dir
                )
                is not None
            )

        if is_new:
            changed.append({"subject": subject, "changes": len(entry_changes)})

    if not dry_run:
        save_checkpoint(checkpoint_path, when.isoformat())

    return changed


def log_cycle(changed: list[dict[str, Any]], label: str = "") -> None:
    """
    Printed only when there is something to read — `docker_events
    _monitor.log_cycle`'s own reasoning, unchanged: a monitor polling
    every `POLL_SECONDS` that logged every quiet cycle (most of them,
    for a host whose containers are not actively drifting) would bury
    the one line that matters.

    `changed=`, not `new=` — deliberately a different word from
    `docker_events_monitor.log_cycle`'s own line: every Docker event
    that stream reports is inherently new (Docker itself never
    repeats one), but a subject appearing here means its filesystem
    diff *changed* since the last time this monitor recorded it,
    which is the real, and different, thing being counted.
    """

    if not (changed or label):
        return

    prefix = f"{label}: " if label else ""
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    subjects = sorted({str(entry["subject"]) for entry in changed})

    print(f"{when} {prefix}changed={len(changed)} subjects={subjects}")


def main(argv: list[str] | None = None) -> None:

    # Line-buffer stdout under systemd — the same defect
    # `docker_events_monitor.main`'s own comment documents and fixes.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    checkpoint_path, generated_dir, once, dry_run = parse(
        sys.argv[1:] if argv is None else argv
    )

    # `ADR-0011` § 9 (R11) — detected once, here, before the first
    # cycle of this process's own run, the same placement
    # `docker_events_monitor.main`'s own comment already explains:
    # this must read the *pre-existing* checkpoint (this process's
    # last-known coverage before it started again), not the one
    # `run_cycle`'s own first iteration is about to overwrite.
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

    try:
        while True:
            changed = run_cycle(generated_dir, checkpoint_path, dry_run)

            # `--once` always prints — the same incident
            # `docker_events_monitor.FIRST_RUN_LOOKBACK_SECONDS`'s own
            # comment names: a manual check that stays silent on a
            # quiet cycle looks indistinguishable from one that never
            # ran at all.
            log_cycle(changed, label="check" if once else "")

            if once:
                return

            time.sleep(POLL_SECONDS)

    except (KeyboardInterrupt, _Stop):
        log_cycle([], label="stopping")


if __name__ == "__main__":
    main()
