from __future__ import annotations

import sys
import uuid
from pathlib import Path

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.boot_check import DEFAULT_GENERATED_DIR, BootCheckTask

USAGE = (
    "usage: python -m aistack.cli.boot_check "
    "[--once] [--facts DIR] [--output DIR] [--definition PATH] [--no-cockpit] [--dry-run] [--suggest]\n"
    "\n"
    "  Judges the facts the host unit aistack-boot-facts wrote (ADR-0032) against\n"
    "  what boot_checks.yml declares a healthy start to be, and writes the verdict.\n"
    "\n"
    "  --once         accepted for symmetry with the other commands: one pass is all it does.\n"
    "  --facts        the folder of boot-facts.json (default: <output>/boot-host).\n"
    "  --output       where boot-check.json is written (default: reports/generated).\n"
    "  --definition   path to the declaration (default: the shipped one, or yours).\n"
    "  --no-cockpit   do not read the disks and backups of the health cockpit.\n"
    "  --dry-run      judge and say, write nothing.\n"
    "  --suggest      print what the facts say as a declaration to copy into your\n"
    "                 boot_checks.yml (containers, mounts, rules, probes). Nothing is written.\n"
    "\n"
    "  Exit code: 0 well or being checked, 1 to watch, 2 to fix, 3 not judged.\n"
)


def parse(argv: list[str]) -> dict[str, object]:
    """The command line as the payload of the `boot.check` Task."""

    payload: dict[str, object] = {"generated_dir": DEFAULT_GENERATED_DIR}
    rest = list(argv)
    paths = {"--facts": "facts_dir", "--output": "generated_dir", "--definition": "definition"}
    flags = {"--no-cockpit": ("cockpit", False), "--dry-run": ("dry_run", True), "--suggest": ("suggest", True)}

    while rest:
        argument = rest.pop(0)

        if argument in ("-h", "--help"):
            print(USAGE)
            raise SystemExit(0)

        if argument in paths:
            if not rest:
                print(f"{argument} expects a path")
                raise SystemExit(2)

            payload[paths[argument]] = rest.pop(0)
        elif argument in flags:
            payload[flags[argument][0]] = flags[argument][1]
        elif argument != "--once":
            print(f"unknown argument: {argument}\n\n{USAGE}")
            raise SystemExit(2)

    return payload


def main(argv: list[str] | None = None) -> int:
    """
    Judge how the host started (`ADR-0032`, slice B2): the Runtime executes
    the `boot.check` Task, which reads the facts and writes only its own
    verdict. The exit code says how the start looks.
    """

    payload = parse(sys.argv[1:] if argv is None else argv)
    generated_dir = Path(str(payload["generated_dir"]))
    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository(output_path=generated_dir / "execution-trace.json"))
    request = Request(request_id=str(uuid.uuid4()), task_id=BootCheckTask.task_id, payload=payload)
    data = runtime.execute(request).observation.data

    print(data["text"])

    return int(data["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
