from __future__ import annotations

import json
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.generators.collection_gap import record_collection_gap
from aistack.providers.docker.packages import (
    collect_packages_on_image_change,
    collect_running_container_packages,
)
from aistack.providers.docker.packages_history import (
    DEFAULT_GENERATED_DIR,
    has_changed,
    record_package_inventory,
)

# Same value as `aistack.timemachine.projection.docker_packages.STREAM_STEM`.
STREAM_STEM = "docker-packages"

POLL_SECONDS = 10.0

DEFAULT_CHECKPOINT_PATH = Path("reports/generated/docker-packages/checkpoint.json")

USAGE = (
    "usage: python -m aistack.cli.docker_packages_monitor "
    "[--checkpoint PATH] [--generated-dir PATH] [--once] [--dry-run]\n"
    "\n"
    "  Takes every running container's own package inventory once at\n"
    "  startup, then again only when its image digest changes\n"
    "  (`docker exec` + `dpkg-query`, falling back to\n"
    "  `/lib/apk/db/installed`) and records a\n"
    "  subject's own observation to Observation History only when it\n"
    "  differs from what was last recorded for it.\n"
    "\n"
    "  --once        run a single poll/record cycle and exit,\n"
    "                instead of looping — for a first manual check\n"
    "                against the real Docker daemon.\n"
    "  --dry-run     print which subjects would be recorded without\n"
    "                writing anything or advancing the checkpoint —\n"
    "                the same distinction every other 1.5 monitor's\n"
    "                own `--dry-run` already draws.\n"
    "  --checkpoint  path to this monitor's own R11 checkpoint file,\n"
    "                which only ever records when this process's own\n"
    "                cycles last ran (default: the real one this\n"
    "                repository ships) — unrelated to the per-subject\n"
    "                `docker-packages.json` write-on-change comparison,\n"
    "                which reads each subject's own stable \"latest\"\n"
    "                file instead (`aistack.providers.docker\n"
    "                .packages_history.has_changed`).\n"
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
    When this monitor's last cycle ran, or None on a first run or unreadable file.

    Used only by R11 (`record_collection_gap`) to measure a restart gap.
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
    seen_digests: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """
    Record each running container's package inventory where it changed.

    The checkpoint advances on every non-dry-run cycle, even a quiet one,
    so R11 measures gaps from the last real coverage. Returns
    `{"subject", "mechanism", "package_count"}` per changed subject, in
    dry-run mode too.
    """

    when = now if now is not None else datetime.now(timezone.utc)
    # With `seen_digests`, only containers whose image changed are probed
    # again; without it every running container is.
    inventories = (
        collect_packages_on_image_change(seen_digests)
        if seen_digests is not None
        else collect_running_container_packages()
    )

    changed: list[dict[str, Any]] = []
    for entry in inventories:
        subject = entry["subject"]
        mechanism = entry["mechanism"]
        packages = entry["packages"]

        if dry_run:
            is_new = has_changed(
                subject, mechanism, packages, generated_dir=generated_dir
            )
        else:
            is_new = (
                record_package_inventory(
                    subject, mechanism, packages, generated_dir=generated_dir
                )
                is not None
            )

        if is_new:
            changed.append(
                {
                    "subject": subject,
                    "mechanism": mechanism,
                    "package_count": len(packages),
                }
            )

    if not dry_run:
        save_checkpoint(checkpoint_path, when.isoformat())

    return changed


def log_cycle(changed: list[dict[str, Any]], label: str = "") -> None:
    """Print a line only when something changed or `label` is set, so quiet cycles stay silent."""

    if not (changed or label):
        return

    prefix = f"{label}: " if label else ""
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    subjects = sorted({str(entry["subject"]) for entry in changed})

    print(f"{when} {prefix}changed={len(changed)} subjects={subjects}")


def main(argv: list[str] | None = None) -> None:

    # Line-buffer stdout so each line reaches journald at once.
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    checkpoint_path, generated_dir, once, dry_run = parse(
        sys.argv[1:] if argv is None else argv
    )

    # ADR-0011 § 9 (R11): check for a gap before the first cycle, against
    # the checkpoint the previous run left.
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

    # Empty at start: the first cycle inventories every running container,
    # later cycles only those whose image digest changed.
    seen_digests: dict[str, str] = {}

    try:
        while True:
            changed = run_cycle(
                generated_dir, checkpoint_path, dry_run, seen_digests=seen_digests
            )

            # `--once` always prints, so a quiet manual check is not mistaken for no run.
            log_cycle(changed, label="check" if once else "")

            if once:
                return

            time.sleep(POLL_SECONDS)

    except (KeyboardInterrupt, _Stop):
        log_cycle([], label="stopping")


if __name__ == "__main__":
    main()
