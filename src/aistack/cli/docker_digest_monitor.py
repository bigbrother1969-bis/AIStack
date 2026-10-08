from __future__ import annotations

import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.generators.collection_gap import record_collection_gap
from aistack.providers.docker.digest import collect_running_container_digests, image_repo_digests
from aistack.providers.docker.digest_history import (
    DEFAULT_GENERATED_DIR,
    has_changed,
    record_image_digest,
)

# `aistack.timemachine.projection.docker_digest.STREAM_STEM`
# redeclared here — the same cross-boundary convention
# `aistack.cli.docker_diff_monitor.STREAM_STEM`'s own comment already
# names.
STREAM_STEM = "docker-digest"

# Cadrage 2026-09-28 (1.5's third collector): the same governed
# polling loop `aistack.cli.docker_diff_monitor` already established
# for the second one, unchanged — not tuned against a real
# measurement, the owner's own decision to change with a single edit
# here if it ever needs to.
POLL_SECONDS = 10.0

DEFAULT_CHECKPOINT_PATH = Path("reports/generated/docker-digest/checkpoint.json")

USAGE = (
    "usage: python -m aistack.cli.docker_digest_monitor "
    "[--checkpoint PATH] [--generated-dir PATH] [--once] [--dry-run]\n"
    "\n"
    "  Polls every running container's own current image digest each\n"
    "  cycle (`docker inspect`'s own `.Image`, the image's own\n"
    "  configuration digest — `aistack.providers.docker.identity`'s\n"
    "  own comment explains exactly which one and why) and records a\n"
    "  subject's own observation to Observation History only when it\n"
    "  differs from what was last recorded for it — a changed digest\n"
    "  for a stable subject is the local proof an upgrade happened.\n"
    "\n"
    "  --once        run a single poll/record cycle and exit,\n"
    "                instead of looping — for a first manual check\n"
    "                against the real Docker daemon.\n"
    "  --dry-run     print which subjects would be recorded without\n"
    "                writing anything or advancing the checkpoint —\n"
    "                the same distinction `docker_diff_monitor\n"
    "                --dry-run` already draws for its own stream.\n"
    "  --checkpoint  path to this monitor's own R11 checkpoint file,\n"
    "                which only ever records when this process's own\n"
    "                cycles last ran (default: the real one this\n"
    "                repository ships) — unrelated to the per-subject\n"
    "                `docker-digest.json` write-on-change comparison,\n"
    "                which reads each subject's own stable \"latest\"\n"
    "                file instead (`aistack.providers.docker\n"
    "                .digest_history.has_changed`).\n"
    "  --generated-dir  root both `record_collection_gap` (R11) and\n"
    "                every per-subject observation are written under\n"
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
    on a first run — the same contract
    `aistack.cli.docker_diff_monitor.load_checkpoint` already holds,
    for the same reason: this monitor polls current state each cycle,
    with no window to bound, so this checkpoint exists solely so R11
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
    One poll: every running container's current image digest
    (`aistack.providers.docker.digest
    .collect_running_container_digests`), recorded per subject only
    where it actually changed.

    **The checkpoint advances every non-dry-run cycle, whether or not
    anything changed** — the same reasoning
    `docker_diff_monitor.run_cycle`'s own docstring gives for its own
    checkpoint: a quiet cycle, with every container's digest
    unchanged, must still move this monitor's own "last known
    coverage" forward, or a later restart's R11 gap-check would
    measure from stale, arbitrarily old state instead.

    Returns one entry per subject that actually changed this cycle
    (`{"subject", "digest"}`) — in both dry-run and normal mode, so a
    manual `--once --dry-run` check reports exactly what a real run
    would have recorded, without writing anything itself.
    """

    when = now if now is not None else datetime.now(timezone.utc)
    digests = collect_running_container_digests()

    changed: list[dict[str, Any]] = []
    for entry in digests:
        subject = entry["subject"]
        digest = entry["digest"]

        if dry_run:
            is_new = has_changed(subject, digest, generated_dir=generated_dir)
        else:
            # The registry digests are looked up only when the digest
            # changed: one `docker image inspect` per upgrade, not per
            # container per poll.
            is_new = has_changed(subject, digest, generated_dir=generated_dir) and (
                record_image_digest(
                    subject,
                    digest,
                    image=str(entry.get("image") or ""),
                    repo_digests=image_repo_digests(digest),
                    generated_dir=generated_dir,
                )
                is not None
            )

        if is_new:
            changed.append({"subject": subject, "digest": digest})

    if not dry_run:
        save_checkpoint(checkpoint_path, when.isoformat())

    return changed


def log_cycle(changed: list[dict[str, Any]], label: str = "") -> None:
    """
    Printed only when there is something to read — the same reasoning
    `docker_diff_monitor.log_cycle` already holds: a monitor polling
    every `POLL_SECONDS` that logged every quiet cycle (most of them)
    would bury the one line that matters.
    """

    if not (changed or label):
        return

    prefix = f"{label}: " if label else ""
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    subjects = sorted({str(entry["subject"]) for entry in changed})

    print(f"{when} {prefix}changed={len(changed)} subjects={subjects}")


def main(argv: list[str] | None = None) -> None:

    # Line-buffer stdout under systemd — the same defect
    # `docker_diff_monitor.main`'s own comment documents and fixes.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    checkpoint_path, generated_dir, once, dry_run = parse(
        sys.argv[1:] if argv is None else argv
    )

    # `ADR-0011` § 9 (R11) — detected once, here, before the first
    # cycle of this process's own run, the same placement
    # `docker_diff_monitor.main`'s own comment already explains: this
    # must read the *pre-existing* checkpoint (this process's last-
    # known coverage before it started again), not the one
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
            # `docker_diff_monitor.main`'s own comment names: a manual
            # check that stays silent on a quiet cycle looks
            # indistinguishable from one that never ran at all.
            log_cycle(changed, label="check" if once else "")

            if once:
                return

            time.sleep(POLL_SECONDS)

    except (KeyboardInterrupt, _Stop):
        log_cycle([], label="stopping")


if __name__ == "__main__":
    main()
