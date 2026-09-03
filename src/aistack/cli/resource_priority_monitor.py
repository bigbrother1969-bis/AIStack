from __future__ import annotations

import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.priority.apply import ApplyReport, apply_resource_priority
from aistack.priority.definition import ResourcePriorityDefinition
from aistack.priority.grace import GraceState, resolve_boosted
from aistack.priority.playback import has_active_playback
from aistack.priority.targets import resolve_resource_targets
from aistack.priority.yaml import load_resource_priority_yaml
from aistack.providers.jellyfin import JellyfinProvider


# Étape 4 of claude/PLAN-RESOURCE-PRIORITY-2026-09-03.md — the loop
# that ties étapes 1-3 together: ask Jellyfin, decide, apply.
#
# Polling and grace-period values are the owner's own decisions of
# 2026-09-03, not tuned here.
POLL_SECONDS = 5.0
GRACE_SECONDS = 60.0

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
    "  Polls Jellyfin every 5 seconds and keeps every governed\n"
    "  container's CPU ceiling in sync with whether Jellyfin is\n"
    "  being watched.\n"
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


def is_playing_now(provider: JellyfinProvider) -> bool:
    """
    Decision #4: an unreachable Jellyfin reads as "not playing".

    A supervision failure must not starve the background containers
    indefinitely, so the fallback is full power for them — accepted
    cost: Jellyfin itself may then contend with them on a day its
    own API is down, which decision #4 already weighed against the
    alternative and chose.
    """

    observation = provider.collect()["jellyfin"]

    if not observation["reachable"]:
        return False

    return has_active_playback(observation["sessions"])


def run_cycle(
    definition: ResourcePriorityDefinition,
    provider: JellyfinProvider,
    grace_state: GraceState,
    dry_run: bool,
) -> tuple[bool, GraceState, ApplyReport]:
    """
    One poll, one decision, one application — everything the loop
    below repeats, in a shape a caller can also run once.
    """

    boosted, next_state = resolve_boosted(
        playing_now=is_playing_now(provider),
        now=time.monotonic(),
        grace_seconds=GRACE_SECONDS,
        state=grace_state,
    )

    targets = resolve_resource_targets(definition, playing=boosted)

    report = apply_resource_priority(
        targets, unlimited_cpus=definition.unlimited_cpus, dry_run=dry_run
    )

    return boosted, next_state, report


def log_cycle(boosted: bool, report: ApplyReport, label: str = "") -> None:
    """
    Printed, not silent, but only when there is something to read.

    A monitor polling every 5 seconds that logged every poll would
    bury the one line that matters under thousands that do not —
    printed only when something changed, or on the explicit
    shutdown line `label` carries.

    **Timestamped, so a transition can be checked against the
    grace period rather than guessed at.** Found needed 2026-09-03:
    the owner watched a restore that looked faster than 60 seconds,
    and there was no timestamp on either the "boosted" or the
    "normal" line to check it against — only two log lines and an
    unknown gap between them. Wall-clock (`datetime.now`), not
    `time.monotonic()`: this is for a human reading a terminal
    against their own watch, not for the grace-period arithmetic
    itself, which stays on the monotonic clock in `grace.py`.
    """

    if not (report.applied or report.failed or report.not_found or label):
        return

    prefix = f"{label}: " if label else ""
    when = datetime.now(timezone.utc).isoformat(timespec="seconds")

    print(
        f"{when} {prefix}state={'boosted' if boosted else 'normal'} "
        f"applied={list(report.applied)} "
        f"not_found={list(report.not_found)} "
        f"failed={list(report.failed)}"
    )


def main(argv: list[str] | None = None) -> None:

    definition_path, once, dry_run = parse(
        sys.argv[1:] if argv is None else argv
    )

    definition = load_resource_priority_yaml(definition_path)

    provider = JellyfinProvider(
        definition.jellyfin.url,
        os.environ.get(definition.jellyfin.api_key_env, ""),
        timeout=definition.jellyfin.timeout_seconds,
    )

    grace_state = GraceState()
    boosted = False

    def handle_sigterm(signum: int, frame: Any) -> None:
        raise _Stop()

    if not once:
        signal.signal(signal.SIGTERM, handle_sigterm)

    try:
        while True:
            boosted, grace_state, report = run_cycle(
                definition, provider, grace_state, dry_run
            )

            log_cycle(boosted, report)

            if once:
                return

            time.sleep(POLL_SECONDS)

    except (KeyboardInterrupt, _Stop):
        pass

    finally:
        # A stopped monitor should not be the reason the background
        # containers stay throttled — decision #4's own reasoning
        # ("a supervision failure must not starve them indefinitely")
        # applies as much to this process dying as to Jellyfin
        # becoming unreachable. Best-effort and never raised: a
        # failure here must not hide why the process actually exited.
        if not once and boosted:
            try:
                release = apply_resource_priority(
                    resolve_resource_targets(definition, playing=False),
                    unlimited_cpus=definition.unlimited_cpus,
                    dry_run=dry_run,
                )
                log_cycle(False, release, label="releasing on exit")
            except Exception as error:
                print(
                    "resource-priority-monitor: could not release on "
                    f"exit: {error}"
                )


if __name__ == "__main__":
    main()
