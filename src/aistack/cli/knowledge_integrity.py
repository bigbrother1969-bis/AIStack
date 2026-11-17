from __future__ import annotations

import sys
import uuid
from pathlib import Path

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.knowledge_integrity import DEFAULT_BUNDLE, KnowledgeIntegrityTask

LABELS = {
    "blocking": "BLOCKING",
    "warning": "WARNING",
    "observation": "OBSERVED",
}


def main() -> None:
    """
    Check a Context Bundle and print what the integrity checks observed.

    The Runtime executes the `knowledge.integrity` Task (`ADR-0027` § 13)
    and keeps its trace under `reports/generated/history/execution-trace/`.
    The optional argument is the bundle (default
    `context/bundles/AIStack-Context-Bundle.zip`). The command exits 1 when
    something blocks, 2 when the bundle is not there.
    """

    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_BUNDLE)

    if not target.exists():
        print(f"Bundle not found: {target}")
        raise SystemExit(2)

    runtime = KernelRuntime.boot(trace_repository=FileTraceRepository())

    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=KnowledgeIntegrityTask.task_id,
        payload={"bundle": str(target)},
    )

    data = runtime.execute(request).observation.data

    print("Knowledge Integrity Report")
    print(f"- Bundle: {data['bundle_id']}")
    print(f"- Source commit: {data['source_commit']}")
    print(f"- Artifacts: {data['artifact_count']}")
    print("")

    if not data["findings"]:
        print("No finding.")

    for finding in data["findings"]:
        print(f"[{LABELS[finding['severity']]}] {finding['check']}: {finding['summary']}")
        print(f"    {finding['affected']}/{finding['total']} {finding['unit']}")

    print("")
    print(f"blocking: {data['blocking']}   warnings: {data['warnings']}   clean: {data['clean']}")

    if data["blocking"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
