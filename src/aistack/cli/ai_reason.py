from __future__ import annotations

import uuid
from typing import Any

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.ai_reason import AiReasonTask


def report(finding: dict[str, Any], answers: list[dict[str, Any]]) -> None:
    print(f"[{finding['subject']}] {finding['signature']}")
    print(f"    {finding['interpretation']}")
    print("")

    for answer in answers:
        print(f"  {answer['operation']}:")

        if not answer["reachable"]:
            print(f"    (not answered \u2014 {answer['unreachable_reason']})")
            print("")
            continue

        for line in answer["response"].strip().splitlines():
            print(f"    {line}")

        print("")


def main() -> None:
    """
    Reason about the host's findings with the AI runtime, on demand.

    The Runtime executes the `ai.reason` Task (ADR-0027 § 10) and keeps
    its trace under `reports/generated/history/execution-trace/`.
    """

    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository())

    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=AiReasonTask.task_id,
    )

    data = runtime.execute(request).observation.data

    if data["note"]:
        print(f"AI Runtime: {data['note']}")

    if not data["findings"]:
        print("No qualified finding to reason about right now.")
        return

    for finding in data["findings"]:
        report(finding, finding["answers"])


if __name__ == "__main__":
    main()
