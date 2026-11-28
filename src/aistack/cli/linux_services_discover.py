from __future__ import annotations

import uuid

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.linux_services_discover import LinuxServicesDiscoverTask


def main() -> None:
    """
    Scan the network for the four target Linux services outside Docker
    (MariaDB/MySQL, PostgreSQL, Apache, PHP) and write a separate JSON
    report.

    Run on demand only, never from `architecture_render`: an SSH scan
    is an action, not a passive read. The Runtime executes the
    `linux_services.discover` Task (`ADR-0035`) and keeps its trace
    under `reports/generated/history/execution-trace/`.
    """

    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository())

    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=LinuxServicesDiscoverTask.task_id,
    )

    data = runtime.execute(request).observation.data

    print(f"Linux services observation written to {data['output_path']}")
    print(f"Linux services catalog written to {data['catalog_output_path']} ({data['catalog_items']} item(s))")


if __name__ == "__main__":
    main()
