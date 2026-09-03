from __future__ import annotations

import uuid

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tasks.docker_discover import DEFAULT_OUTPUT_PATH
from aistack.kernel.tracing import FileTraceRepository


def main() -> None:
    # Durable, not the Runtime's own in-memory default — Runtime
    # Operation History (2026-09-03) needs this command's executions
    # to survive the process, the same way every provider's
    # Observation History already does.
    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository())

    # A fresh id per invocation: two runs must be told apart in that
    # history, not just their observations.
    request = Request(
        request_id=str(uuid.uuid4()),
        task_id="docker.discover",
        payload={"output_path": DEFAULT_OUTPUT_PATH},
    )

    trace = runtime.execute(request)

    print(f"Docker observation written to {trace.observation.data['output_path']}")


if __name__ == "__main__":
    main()
