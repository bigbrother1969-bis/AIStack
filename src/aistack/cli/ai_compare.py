from __future__ import annotations

import argparse
import sys
import uuid
from collections.abc import Sequence
from pathlib import Path

from aistack.ai_runtime.operations import _LANGUAGE_DIRECTIVE
from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.ai_compare import AiCompareTask
from aistack.tasks.security_assess import DEFAULT_GENERATED_DIR
from aistack.troubleshooting.guide import OPERATIONS


def main(argv: Sequence[str] | None = None) -> int:
    """
    Put the local engines side by side on the findings of the last security report.

    The Runtime executes the `ai.compare` Task: the same prompts as the Security page, each engine
    alone, with the time of each answer and a few automatic flags; the report is a markdown file
    under `ai-compare/` of the data directory. Nothing on any host is changed and no engine that
    can leave the network is asked. Without `--engine`, every engine of `ai_runtime.yml` is compared.
    With `--dry-run` it only says who would be asked what, and sends nothing. Exit code 2 when
    the request cannot be carried out.
    """

    parser = argparse.ArgumentParser(prog="python -m aistack.cli.ai_compare", description=main.__doc__)
    parser.add_argument("--generated", default=DEFAULT_GENERATED_DIR, help="data directory holding security-assessment.json")
    parser.add_argument("--engine", action="append", default=[], metavar="SPEC", help="kind@host:port/model[?effort=low&label=Olala&timeout=300], repeatable")
    parser.add_argument("--finding", action="append", default=[], metavar="KEY", help="a finding key of the report, repeatable (default: the worst ones)")
    parser.add_argument("--max", type=int, default=2, help="how many findings when none is named (default 2)")
    parser.add_argument("--lang", default="fr", choices=sorted(_LANGUAGE_DIRECTIVE))
    parser.add_argument("--operations", default=",".join(OPERATIONS), help="comma-separated, among reason, explain, recommend")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    generated = Path(args.generated)
    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository(output_path=generated / "execution-trace.json"))
    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=AiCompareTask.task_id,
        payload={
            "generated_dir": str(generated),
            "engines": args.engine,
            "findings": args.finding,
            "max": args.max,
            "language": args.lang,
            "operations": [name.strip() for name in args.operations.split(",") if name.strip()],
            "dry_run": args.dry_run,
        },
    )
    data = runtime.execute(request).observation.data

    if data["refused"]:
        print(f"ai_compare: {data['refused']}", file=sys.stderr)
        return 2

    print(f"Engines  : {', '.join(data['engines'])}")
    print(f"Findings : {', '.join(data['findings'])}")
    print(f"Questions: {data['questions']} ({', '.join(data['operations'])}; one engine at a time)")
    if data["dry_run"]:
        print("Dry run: nothing was asked.")
        return 0
    print(f"Report: {data['report_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
