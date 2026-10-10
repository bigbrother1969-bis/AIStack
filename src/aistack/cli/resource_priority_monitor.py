from __future__ import annotations

from aistack.config import configured

import signal
import sys
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.api_keys import apply_to_environ
from aistack.priority.apply import ApplyReport, apply_resource_priority
from aistack.priority.decision_history import record_decision
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.detectors.base import Detector
from aistack.priority.detectors.factory import build_detector
from aistack.priority.grace import GraceState, resolve_boosted
from aistack.priority.targets import resolve_resource_targets
from aistack.priority.yaml import load_resource_priority_yaml


# Each cycle asks every priority app's detector, decides, and applies CPU
# ceilings. The grace period is `ResourcePriorityDefinition.grace_seconds`.
POLL_SECONDS = 5.0

DEFAULT_DEFINITION = (
    configured(Path(__file__).resolve().parents[1]
    / "priority"
    / "definitions"
    / "resource_priority.yml")
)

USAGE = (
    "usage: python -m aistack.cli.resource_priority_monitor "
    "[--definition PATH] [--once] [--dry-run]\n"
    "\n"
    "  Polls every governed priority app's own detector and keeps\n"
    "  every governed container's CPU ceiling in sync with which of\n"
    "  them, if any, is active.\n"
    "\n"
    "  --once        run a single poll/decide/apply cycle and\n"
    "                exit, instead of looping — for a first\n"
    "                manual check against the real containers.\n"
    "  --dry-run     report what would change without calling\n"
    "                `docker update`.\n"
    "  --definition  path to the governed YAML (default: the real\n"
    "                one this repository ships).\n"
)


class _Stop(Exception):
    """Raised from the SIGTERM handler to unwind the loop cleanly."""


def parse(argv: list[str]) -> tuple[Path, bool, bool]:

    definition_path = DEFAULT_DEFINITION
    once = False
    dry_run = False
    rest = list(argv)

    while rest:
        argument = rest.pop(0)

        if argument in ("-h", "--help"):
            print(USAGE)
            raise SystemExit(0)

        if argument == "--definition":
            if not rest:
                print("--definition expects a path")
                raise SystemExit(2)
            definition_path = Path(rest.pop(0))
            continue

        if argument == "--once":
            once = True
            continue

        if argument == "--dry-run":
            dry_run = True
            continue

        print(f"unrecognised argument: {argument}")
        raise SystemExit(2)

    return definition_path, once, dry_run


def build_detectors(
    definition: ResourcePriorityDefinition,
) -> dict[str, Detector]:
    """One detector per priority app, keyed by container name; built once and reused every poll."""

    return {
        app.container: build_detector(app) for app in definition.priority
    }


def run_cycle(
    definition: ResourcePriorityDefinition,
    detectors: Mapping[str, Detector],
    grace_states: Mapping[str, GraceState],
    dry_run: bool,
) -> tuple[dict[str, bool], dict[str, GraceState], ApplyReport]:
    """
    One poll: decide per priority app, then apply the resulting ceilings.

    Each app's `GraceState` advances independently from its own detector,
    all read against the same `now`.
    """

    now = time.monotonic()
    boosted: dict[str, bool] = {}
    next_states: dict[str, GraceState] = {}

    for app in definition.priority:
        app_boosted, next_state = resolve_boosted(
            playing_now=detectors[app.container].is_active(),
            now=now,
            grace_seconds=definition.grace_seconds,
            state=grace_states.get(app.container, GraceState()),
        )
        boosted[app.container] = app_boosted
        next_states[app.container] = next_state

    targets = resolve_resource_targets(definition, boosted)

    report = apply_resource_priority(
        targets, unlimited_cpus=definition.unlimited_cpus, dry_run=dry_run
    )

    return boosted, next_states, report


def log_cycle(
    boosted: Mapping[str, bool], report: ApplyReport, label: str = ""
) -> None:
    """
    Print a timestamped line when `report.changed` or `label` is set.

    `report.changed` is also what `record_decision` persists on, so the
    journal and the history agree. The timestamp is wall-clock, for a
    human; the grace arithmetic stays on the monotonic clock.
    """

    if not (report.changed or label):
        return

    prefix = f"{label}: " if label else ""
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")
    state = ",".join(
        f"{name}={'boosted' if value else 'normal'}"
        for name, value in boosted.items()
    )

    print(
        f"{when} {prefix}state={{{state}}} "
        f"applied={list(report.applied)} "
        f"not_found={list(report.not_found)} "
        f"failed={list(report.failed)}"
    )


def main(argv: list[str] | None = None) -> None:

    # Under systemd stdout is a pipe, which Python block-buffers: a state
    # change could stay out of the journal indefinitely. Line buffering
    # sends each line at once. (`reconfigure` exists on `TextIOWrapper`,
    # not on the `TextIO` type of `sys.stdout`, hence the ignore.)
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]

    definition_path, once, dry_run = parse(
        sys.argv[1:] if argv is None else argv
    )

    # Keys entered from Settings (Jellyfin's), read once here.
    apply_to_environ(Path("reports/generated"))
    definition = load_resource_priority_yaml(definition_path)
    detectors = build_detectors(definition)

    grace_states: dict[str, GraceState] = {
        app.container: GraceState() for app in definition.priority
    }
    boosted: dict[str, bool] = {}

    def handle_sigterm(signum: int, frame: Any) -> None:
        raise _Stop()

    if not once:
        signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        while True:
            boosted, grace_states, report = run_cycle(
                definition, detectors, grace_states, dry_run
            )

            log_cycle(boosted, report)
            record_decision(boosted, report)

            if once:
                return

            time.sleep(POLL_SECONDS)

    except (KeyboardInterrupt, _Stop):
        pass

    finally:
        # A stopped monitor must not leave containers throttled or boosted.
        # Best-effort: a failure here must not hide why the process exited.
        if not once and any(boosted.values()):
            try:
                release = apply_resource_priority(
                    resolve_resource_targets(definition, boosted={}),
                    unlimited_cpus=definition.unlimited_cpus,
                    dry_run=dry_run,
                )
                log_cycle({}, release, label="releasing on exit")
                record_decision({}, release)
            except Exception as error:
                print(
                    "resource-priority-monitor: could not release on "
                    f"exit: {error}"
                )


if __name__ == "__main__":
    main()
