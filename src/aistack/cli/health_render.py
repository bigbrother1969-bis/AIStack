from __future__ import annotations

import uuid

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.health_render import HealthRenderTask


def main() -> None:
    """
    Render the health cockpit, its scores, the action plan and the vigil snapshot.

    The Runtime executes the `health.render` Task (ADR-0027 § 10) and
    keeps its trace under `reports/generated/history/execution-trace/`:
    durable, not the Runtime's in-memory default, so the history of what
    the Runtime executed survives the process.
    """

    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository())

    # A fresh id per run: two runs must be told apart in that history.
    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=HealthRenderTask.task_id,
    )

    data = runtime.execute(request).observation.data

    if data["score"] is not None:
        print(
            f"Health cockpit written to {data['output_path']} "
            f"(score: {data['score']}/100, {data['score_bucket']}, "
            f"{data['measured_domains']}/{data['total_domains']} domain(s) measured)"
        )
    else:
        print(f"Health cockpit written to {data['output_path']} (score: {data['score_note']})")

    if data["debt_score"] is not None:
        print(
            f"Technical-debt score: {data['debt_score']}/100, {data['debt_bucket']}, "
            f"{data['debt_findings']} finding(s)"
        )
    else:
        print(f"Technical-debt score: {data['debt_note']}")

    print(f"Action plan written to {data['plan_path']}")


if __name__ == "__main__":
    main()
