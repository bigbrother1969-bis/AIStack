from __future__ import annotations

import uuid

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.network_docker_discover import NetworkDockerDiscoverTask


def main() -> None:
    """
    Scan the network for Docker hosts and write a separate JSON report.

    Run on demand only, never from `architecture_render`: a network scan
    with SSH attempts is an action, not a passive read. The Runtime
    executes the `network_docker.discover` Task (ADR-0027 § 10) and keeps
    its trace under `reports/generated/history/execution-trace/`.
    """

    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository())

    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=NetworkDockerDiscoverTask.task_id,
    )

    data = runtime.execute(request).observation.data

    print(f"Network Docker observation written to {data['output_path']}")


if __name__ == "__main__":
    main()
