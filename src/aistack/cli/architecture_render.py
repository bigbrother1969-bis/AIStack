from __future__ import annotations

import uuid

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.architecture_render import ArchitectureRenderTask


def main() -> None:
    """
    Render `architecture.html` and its translations.

    The Runtime executes the `architecture.render` Task (ADR-0027 § 10)
    and keeps its trace beside the others, under
    `reports/generated/history/execution-trace/`. The Task reads the
    environment itself (Beszel credentials): a request is traced and
    must carry none.
    """

    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository())

    # A fresh id per run: two runs must be told apart in that history.
    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=ArchitectureRenderTask.task_id,
    )

    data = runtime.execute(request).observation.data

    print(
        f"Architecture diagram written to {data['output_path']} "
        f"({', '.join(data['pages'])})"
    )


if __name__ == "__main__":
    main()
