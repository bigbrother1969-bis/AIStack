"""
`python -m aistack.cli.security_window` — the maintenance window (ADR-0028, T4a).

    python -m aistack.cli.security_window --for 2h     open a window for two hours
    python -m aistack.cli.security_window --end        close it now
    python -m aistack.cli.security_window --show       say whether one is open

While a window is open, the vigil counts the drift of files and units on
the hosts and does not tell Gotify about it: it is your own doing. Open
ports, secrets, failed logins and the proxy keep being told. A window is
at most `window_max_hours` long (`security.yml`, 4 by default) and ends by
itself. The Runtime executes the `security.window` Task; nothing is
changed on any host. The optional argument is the data directory.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.security.window import zone
from aistack.tasks.security_window import DEFAULT_GENERATED_DIR, END, OPEN, SHOW, SecurityWindowTask


def _say(data: Mapping[str, Any]) -> str:
    if not data["open"]:
        return "No window is open."

    until = datetime.fromisoformat(str(data["until"])).astimezone(zone(str(data["zone"]))).strftime("%H:%M")
    return f"A maintenance window is open until {until} ({data['minutes_left']} min left)."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m aistack.cli.security_window", description=__doc__.split("\n\n")[0])
    what = parser.add_mutually_exclusive_group()
    what.add_argument("--for", dest="duration", metavar="DURATION", help="open a window: 2h, 90m")
    what.add_argument("--end", action="store_true", help="close the window now")
    what.add_argument("--show", action="store_true", help="say whether a window is open (the default)")
    parser.add_argument("generated_dir", nargs="?", default=DEFAULT_GENERATED_DIR, help="the data directory")
    args = parser.parse_args(argv)
    generated_dir = Path(args.generated_dir)

    runtime = KernelRuntime.boot(
        trace_repository=FileTraceRepository(output_path=generated_dir / "execution-trace.json")
    )
    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=SecurityWindowTask.task_id,
        payload={
            "generated_dir": str(generated_dir),
            "action": OPEN if args.duration else END if args.end else SHOW,
            "duration": args.duration or "",
        },
    )
    data = runtime.execute(request).observation.data

    if not data["ok"]:
        print(f"Not opened: {data['error']}")
        return 2

    if args.end:
        print("The window is closed." if data["ended"] else "No window is open.")
        return 0

    print(_say(data))
    return 0


if __name__ == "__main__":
    sys.exit(main())
