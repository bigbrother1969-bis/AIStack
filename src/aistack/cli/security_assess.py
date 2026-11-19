from __future__ import annotations

import sys
import uuid
from pathlib import Path

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.security.findings import FIX, SEVERITIES, URGENT
from aistack.tasks.security_assess import DEFAULT_GENERATED_DIR, SecurityAssessTask


def main() -> None:
    """
    Assess what this host exposes (`ADR-0028`, slice T1).

    The Runtime executes the `security.assess` Task, which reads and
    writes only its own report. The optional argument is the data
    directory. Nothing on the host is changed. Exit code 1 when a finding
    to fix or an urgent one stands, so a caller can tell.
    """

    generated_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_GENERATED_DIR)

    runtime = KernelRuntime.boot(
        trace_repository=FileTraceRepository(output_path=generated_dir / "execution-trace.json")
    )

    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=SecurityAssessTask.task_id,
        payload={"generated_dir": str(generated_dir)},
    )

    data = runtime.execute(request).observation.data
    counts = data["counts"]

    print(
        "Security assessment: "
        + ", ".join(f"{counts[severity]} {severity}" for severity in reversed(SEVERITIES))
        + f" — {data['output_path']}"
    )

    for finding in sorted(data["findings"], key=lambda item: -SEVERITIES.index(item["severity"])):
        print(f"  [{finding['severity']}] {finding['title']}")
        for line in finding["evidence"]:
            print(f"      {line}")
        if finding["unknown"]:
            print(f"      not known: {finding['unknown']}")

    if counts[FIX] or counts[URGENT]:
        sys.exit(1)


if __name__ == "__main__":
    main()
