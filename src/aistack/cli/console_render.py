from __future__ import annotations

import uuid

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.console_render import DEFAULT_CONSOLE_LINKS, ConsoleRenderTask

__all__ = ["DEFAULT_CONSOLE_LINKS", "main"]


def main() -> None:
    """
    Render the console page with its health and technical-debt scores.

    The Runtime executes the `console.render` Task (ADR-0027 § 10) and
    keeps its trace under `reports/generated/history/execution-trace/`:
    durable, not the Runtime's in-memory default.
    """

    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository())

    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=ConsoleRenderTask.task_id,
    )

    data = runtime.execute(request).observation.data

    print(
        f"Console written to {data['output_path']} "
        f"({data['links']} link(s); {', '.join(data['pages'])}); served from "
        f"{data['served_from']} by aistack.web.server"
    )


if __name__ == "__main__":
    main()
