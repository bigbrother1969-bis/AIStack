from __future__ import annotations

import uuid

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tasks.docker_discover import DEFAULT_OUTPUT_PATH


def main() -> None:
    runtime = KernelRuntime.boot()

    # A fresh id per invocation: once traces are historicised
    # (Runtime Operation History, the reason this command was moved
    # onto the Runtime at all — GOV-0002/OS-041, reopened
    # 2026-09-03), two runs must be told apart, not just their
    # observations.
    request = Request(
        request_id=str(uuid.uuid4()),
        task_id="docker.discover",
        payload={"output_path": DEFAULT_OUTPUT_PATH},
    )

    trace = runtime.execute(request)

    print(f"Docker observation written to {trace.observation.data['output_path']}")


if __name__ == "__main__":
    main()
