from __future__ import annotations

import signal
import sys
import time
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.priority.apply import ApplyReport, apply_resource_priority
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.detectors.base import Detector
from aistack.priority.detectors.factory import build_detector
from aistack.priority.grace import GraceState, resolve_boosted
from aistack.priority.targets import resolve_resource_targets
from aistack.priority.yaml import load_resource_priority_yaml


# Étape 4 of claude/PLAN-RESOURCE-PRIORITY-2026-09-03.md — the loop
# that ties étapes 1-3 together: ask every priority app's detector,
# decide, apply. Generalised 2026-09-03 from one hardcoded detector
# (Jellyfin's own `/Sessions`) to any number, per
# claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md.
#
# Polling is the owner's own decision of 2026-09-03, not tuned here.
# The grace period moved into the governed definition the same day
# (`ResourcePriorityDefinition.grace_seconds`) — it was already the
# owner's decision, just not yet written where the rest of this
# feature's decisions live.
POLL_SECONDS = 5.0

DEFAULT_DEFINITION = (
    Path(__file__).resolve().parents[1]
    / "priority"
    / "definitions"
    / "resource_priority.yml"
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
    """
    One detector per priority app, keyed by container name — built
    once at startup and reused every poll, the same lifetime
    `JellyfinProvider` itself already had in the single-app monitor.
    """

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
    One poll, one decision per priority app, one application —
    everything the loop below repeats, in a shape a caller can also
    run once.

    **Each priority app's own `GraceState` advances independently,**
    from its own detector's `is_active()` alone — decision 4 of
    `claude/PLAN-DYNAMIC-CONTAINER-PRIORITY-2026-09-03.md`. All of
    them are read against the same `now`, so two apps active at
    once share one grace clock reading, not two separately-taken
    ones a few milliseconds apart.
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
    Printed, not silent, but only when there is something to read.

    A monitor polling every 5 seconds that logged every poll would
    bury the one line that matters under thousands that do not —
    printed only when something changed, or on the explicit
    shutdown line `label` carries.

    **Timestamped, so a transition can be checked against the grace
    period rather than guessed at.** Found needed 2026-09-03: the
    owner watched a restore that looked faster than 60 seconds, and
    there was no timestamp on either the "boosted" or the "normal"
    line to check it against. Wall-clock (`datetime.now`), not
    `time.monotonic()`: this is for a human reading a terminal
    against their own watch, not for the grace-period arithmetic
    itself, which stays on the monotonic clock in `grace.py`.

    **`state=` now names every priority app, not one implied
    boolean.** With any number of priority apps possible since
    2026-09-03, a single `state=boosted`/`state=normal` no longer
    says which app that was about.
    """

    if not (report.applied or report.failed or report.not_found or label):
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

    # Under systemd, stdout is a pipe to journald, not a terminal —
    # and Python block-buffers a pipe by default, only flushing on a
    # full buffer or process exit. This process runs for hours and
    # prints one short line per state change, so the default buffer
    # (several KB) can sit unflushed indefinitely: a `docker update`
    # already ran, correctly, with nothing in the journal to show
    # for it.
    #
    # Found needed 2026-09-03: a confirmed state transition — verified
    # independently via `docker inspect` on the affected containers —
    # produced no journal line at all, 28 minutes after the fact,
    # with the service still `active (running)`. Reproduced and fixed
    # live in a disposable sandbox before touching this file: a
    # script printing two lines a few seconds apart, run with stdout
    # redirected to a file and `PYTHONUNBUFFERED` unset (matching
    # this project's systemd unit, which does not set it), left that
    # file empty seconds after both prints had executed; the same
    # script with `line_buffering=True` wrote both lines immediately.
    #
    # Line buffering costs nothing here — this process never writes a
    # partial line — and makes every `print()` reach the journal as
    # soon as it is written, matching what running this by hand in a
    # terminal already looked like. Host-touching (it reconfigures
    # this process's own stdout stream), so verified live rather than
    # in the governed suite, per decision #9.
    sys.stdout.reconfigure(line_buffering=True)

    definition_path, once, dry_run = parse(
        sys.argv[1:] if argv is None else argv
    )

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

            if once:
                return

            time.sleep(POLL_SECONDS)

    except (KeyboardInterrupt, _Stop):
        pass

    finally:
        # A stopped monitor should not be the reason the background
        # containers stay throttled, nor a priority app stay at its
        # boosted ceiling — decision #4's own reasoning ("a
        # supervision failure must not starve them indefinitely")
        # applies as much to this process dying as to a detector
        # becoming unreachable. Best-effort and never raised: a
        # failure here must not hide why the process actually exited.
        if not once and any(boosted.values()):
            try:
                release = apply_resource_priority(
                    resolve_resource_targets(definition, boosted={}),
                    unlimited_cpus=definition.unlimited_cpus,
                    dry_run=dry_run,
                )
                log_cycle({}, release, label="releasing on exit")
            except Exception as error:
                print(
                    "resource-priority-monitor: could not release on "
                    f"exit: {error}"
                )


if __name__ == "__main__":
    main()
