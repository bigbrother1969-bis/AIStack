"""
`python -m aistack.cli.pra_schedule` — scheduled restore tests (2.0).

    python -m aistack.cli.pra_schedule              test every service with a sandbox
                                                    recipe not tested in the last 6 days
    python -m aistack.cli.pra_schedule --all        test them all now
    python -m aistack.cli.pra_schedule wordpress    test this one now
    python -m aistack.cli.pra_schedule --list       the recorded outcomes

Run on the host, from the checkout, by the account AIStack runs as —
`aistack-pra.timer` starts it every Sunday morning
(`deploy/systemd/aistack-pra.service`). Each test is a sandbox restore
(`ADR-0018`): the newest backup, restored beside the live service,
checked, timed and removed — the live service is never touched. Its
outcome is recorded in the data directory (`pra/scheduled.jsonl`) and
counts in the Tests PRA domain of the health cockpit; `pra_tests.yml`
is never rewritten. Waits for the dock executor to finish, and holds
it off while it runs.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from aistack.cli.sandbox import data_dir, restore
from aistack.pra.scheduled import ScheduledTest, after_the_dock, due, read_records, record
from aistack.sandbox.declaration import load_sandbox_declaration
from aistack.sandbox.run import Runner, docker_runner, rto_minutes


def main(argv: list[str] | None = None, runner: Runner = docker_runner, root: Path | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.pra_schedule", description=__doc__.split("\n\n")[0])
    parser.add_argument("services", nargs="*", help="only these services, now")
    parser.add_argument("--all", action="store_true", help="every service with a recipe, now")
    parser.add_argument("--list", action="store_true", help="the recorded outcomes")
    args = parser.parse_args(argv)

    generated = data_dir(root or Path.cwd())
    records = read_records(generated)
    if args.list:
        for test in records:
            line = f"{test.at:%Y-%m-%d %H:%M}  {test.service:<12} {test.status}"
            if test.rto_minutes is not None:
                line += f"  {test.rto_minutes} min"
            if test.failure:
                line += f"  — {test.failure}"
            print(line)
        return 0

    declaration = load_sandbox_declaration()
    known = sorted(declaration.recipes)
    unknown = [s for s in args.services if s not in declaration.recipes]
    if unknown:
        print(f"No sandbox recipe for {', '.join(unknown)} (known: {', '.join(known) or 'none'}).")
        return 2
    if args.services:
        chosen = list(args.services)
    elif args.all:
        chosen = known
    else:
        chosen = due(known, records, datetime.now(timezone.utc))
    if not chosen:
        print("Every service with a recipe was tested in the last 6 days.")
        return 0

    failed = 0
    with after_the_dock(generated):
        for service in chosen:
            print(f"== {service}", flush=True)
            run, report = restore(service, declaration, generated, runner, progress=lambda line: print(line, flush=True))
            seconds = run.recovery_seconds
            test = ScheduledTest(
                service=service,
                at=run.started_at,
                status="success" if run.succeeded else "failed",
                run_id=run.run_id,
                rto_minutes=rto_minutes(seconds) if run.succeeded and seconds is not None else None,
                failure="" if run.succeeded else (run.failure or "a required check failed"),
            )
            record(generated, test)
            failed += 0 if run.succeeded else 1
            print(f"{service}: {'SUCCÈS' if run.succeeded else 'ÉCHEC — ' + test.failure} (rapport : {report})", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
