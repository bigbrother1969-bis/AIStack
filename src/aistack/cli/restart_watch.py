from __future__ import annotations

from aistack.config import configured

import signal
import sys
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from aistack.restart_watch import guard, journal
from aistack.restart_watch.act import Outcome, failed_probes, restart_in_order
from aistack.restart_watch.definition import RestartWatchDefinition
from aistack.restart_watch.detect import find_stuck
from aistack.restart_watch.facts import ContainerFacts, read_facts
from aistack.restart_watch.load import load_restart_watch_yaml
from aistack.restart_watch.order import plan_restart
from aistack.vigil import notify

DEFAULT_DEFINITION = configured(
    Path(__file__).resolve().parents[1] / "restart_watch" / "definitions" / "restart_watch.yml"
)
GENERATED = Path("reports/generated")

USAGE = (
    "usage: python -m aistack.cli.restart_watch "
    "[--definition PATH] [--once] [--dry-run] [--ignore-window]\n"
    "\n"
    "  After a start, finds the containers that came up stuck (unhealthy,\n"
    "  sharing the network of a provider restarted after them, or failing\n"
    "  a probe you declared) and restarts them in the order their\n"
    "  dependencies need (ADR-0025).\n"
    "\n"
    "  --once           run a single cycle and exit.\n"
    "  --dry-run        say what would be restarted, restart nothing.\n"
    "  --ignore-window  act even when the window after the start is over —\n"
    "                   for a manual check on a host that has been up a while.\n"
    "  --definition     path to the declaration (default: the shipped one,\n"
    "                   or the one in the configuration directory).\n"
)


class _Stop(Exception):
    """Raised from the SIGTERM handler to leave the loop cleanly."""


@dataclass
class Watch:
    """What the watch remembers between two cycles."""

    started: float
    seen: dict[str, int] = field(default_factory=dict)
    told_outside: set[str] = field(default_factory=set)
    attempts: guard.Attempts = field(default_factory=dict)


def parse(argv: list[str]) -> tuple[Path, bool, bool, bool]:
    definition_path = DEFAULT_DEFINITION
    once = dry_run = ignore_window = False
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
        elif argument == "--once":
            once = True
        elif argument == "--dry-run":
            dry_run = True
        elif argument == "--ignore-window":
            ignore_window = True
        else:
            print(f"unrecognised argument: {argument}")
            raise SystemExit(2)

    return definition_path, once, dry_run, ignore_window


def window_open(watch: Watch, definition: RestartWatchDefinition, now: float, ignore: bool) -> bool:
    """The window opens when the watch starts — with Docker — and lasts `window_minutes`."""

    return ignore or now < watch.started + definition.window_minutes * 60


def run_cycle(
    watch: Watch,
    definition: RestartWatchDefinition,
    facts: tuple[ContainerFacts, ...],
    failed: frozenset[str],
    *,
    now: float,
    generated: Path,
    dry_run: bool,
    ignore_window: bool,
    restart: Callable[..., tuple[Outcome, ...]] = restart_in_order,
    tell: Callable[[str, str], None] = lambda title, body: None,
) -> list[journal.Entry]:
    """
    One decision: who is stuck, whether to act, what was done.

    A container must be seen stuck `confirm_cycles` cycles in a row before
    anything is done (a healthcheck that flaps, a probe that missed once).
    Returns the entries written, for the caller to print.
    """

    written: list[journal.Entry] = []

    def note(event: str, container: str, reasons: tuple[str, ...] = (), detail: str = "") -> None:
        entry = journal.Entry(journal.now_iso(), event, container, reasons, detail)
        journal.append(generated, entry)
        written.append(entry)

    stuck = {item.name: item for item in find_stuck(facts, failed, definition.never)}
    watch.seen = {name: watch.seen.get(name, 0) + 1 for name in stuck}
    watch.told_outside &= set(stuck)
    confirmed = sorted(name for name, count in watch.seen.items() if count >= definition.confirm_cycles)
    inside = window_open(watch, definition, now, ignore_window)

    if confirmed and not inside:
        for name in confirmed:
            if name not in watch.told_outside:
                watch.told_outside.add(name)
                note(journal.OUTSIDE_WINDOW, name, stuck[name].reasons, "window over, nothing done")

        confirmed = []

    roots = []

    for name in confirmed:
        if guard.allowed(watch.attempts, name, now, definition.max_attempts_per_hour):
            roots.append(name)
        else:
            note(journal.SKIPPED_LIMIT, name, stuck[name].reasons,
                 f"{definition.max_attempts_per_hour} attempts in the last hour")

    if roots:
        plan = plan_restart(roots, facts, definition.after, definition.never)
        order = tuple(
            name for name in plan.order
            if name in roots or guard.allowed(watch.attempts, name, now, definition.max_attempts_per_hour)
        )

        if plan.cycle:
            note(journal.CYCLE, ",".join(plan.order), (), "the declared order loops; ordered by name")

        if not dry_run:
            for name in order:
                guard.record(watch.attempts, name, now)

            guard.write_attempts(generated, watch.attempts)

        outcomes = restart(
            order, definition.probes, definition.wait_seconds, dry_run=dry_run
        )

        for outcome in outcomes:
            reasons = stuck[outcome.name].reasons if outcome.name in stuck else ("dragged",)

            if dry_run:
                note(journal.PLANNED, outcome.name, reasons, "dry run")
            elif outcome.ok:
                note(journal.RESTARTED, outcome.name, reasons, outcome.detail)
                watch.seen.pop(outcome.name, None)
            else:
                note(journal.FAILED, outcome.name, reasons, outcome.detail)
                tell(f"AIStack — {outcome.name}", f"{outcome.name}: {outcome.detail}")

        left = [name for name in order if name not in {o.name for o in outcomes}]

        for name in left:
            note(journal.FAILED, name, (), "not restarted: an earlier container did not come back")

    journal.write_state(
        generated,
        {
            "updated_at": journal.now_iso(),
            "window_open": inside,
            "window_minutes": definition.window_minutes,
            "started_at": watch.started,
            "dry_run": dry_run,
            "stuck": [
                {"name": item.name, "reasons": list(item.reasons), "seen": watch.seen.get(item.name, 0)}
                for item in stuck.values()
            ],
        },
    )

    return written


def _gotify_tell() -> Callable[[str, str], None]:
    gotify = notify.Gotify.from_environment()

    def tell(title: str, body: str) -> None:
        if gotify is None:
            return

        try:
            gotify.send(notify.Message(title, body, notify.URGENT))
        except OSError as error:
            print(f"restart-watch: Gotify did not take the message ({error})", flush=True)

    return tell


def main(argv: list[str] | None = None) -> None:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[union-attr]
    definition_path, once, dry_run, ignore_window = parse(sys.argv[1:] if argv is None else argv)
    definition = load_restart_watch_yaml(definition_path)

    if once:
        # A single cycle cannot see anything twice in a row.
        definition = replace(definition, confirm_cycles=1)

    watch = Watch(started=time.time(), attempts=guard.read_attempts(GENERATED))
    tell = _gotify_tell()

    def handle_sigterm(signum: int, frame: Any) -> None:
        raise _Stop()

    if not once:
        signal.signal(signal.SIGTERM, handle_sigterm)

    print(
        f"restart-watch: window {definition.window_minutes} min from now"
        f"{' (ignored)' if ignore_window else ''}, dry-run={dry_run}",
        flush=True,
    )

    try:
        while True:
            try:
                facts = read_facts()
                failed = failed_probes(_probes_of(definition, facts))
                entries = run_cycle(
                    watch, definition, facts, failed,
                    now=time.time(), generated=GENERATED,
                    dry_run=dry_run, ignore_window=ignore_window, tell=tell,
                )

                for line in journal.describe(entries):
                    print(line, flush=True)
            except (RuntimeError, ValueError, OSError) as error:
                print(f"restart-watch: cycle skipped ({error})", flush=True)

            if once:
                return

            time.sleep(definition.poll_seconds)
    except (KeyboardInterrupt, _Stop):
        pass


def _probes_of(definition: RestartWatchDefinition, facts: tuple[ContainerFacts, ...]) -> Mapping[str, Any]:
    """Probe only the declared containers that run and have no healthcheck of their own."""

    running = {item.name for item in facts if item.running and not item.has_healthcheck}

    return {name: probe for name, probe in definition.probes.items() if name in running}


if __name__ == "__main__":
    main()
