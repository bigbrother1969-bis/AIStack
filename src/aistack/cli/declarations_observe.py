from __future__ import annotations

import sys
import uuid
from pathlib import Path

from aistack.config import config_dir
from aistack.declaration import observe
from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.declarations_observe import DEFAULT_GENERATED_DIR, DeclarationsObserveTask


def main() -> None:
    """
    Record the declarations edited by hand on the host (`ADR-0027` § 12).

    The Runtime executes the `declarations.observe` Task, which reads; the
    snapshots and the records are written through the Kernel's transaction
    service. The optional argument is the data directory. The vigil runs it
    at every pass, so an edit is seen at the next pass at the latest.
    """

    generated_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(DEFAULT_GENERATED_DIR)
    directory = config_dir()

    runtime = KernelRuntime.boot(
        trace_repository=FileTraceRepository(output_path=generated_dir / "execution-trace.json")
    )

    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=DeclarationsObserveTask.task_id,
        payload={"generated_dir": str(generated_dir), "config_dir": str(directory or "")},
    )

    data = runtime.execute(request).observation.data

    if directory is None:
        print("No configuration directory: nothing to observe (the shipped files are read).")
        return

    changes = [observe.Observed(**item) for item in data["changes"]]
    records, problems = observe.apply(runtime.kernel.services.transactions, directory, generated_dir, changes)

    reference = sum(1 for item in changes if item.kind == observe.REFERENCE)
    followed = sum(1 for item in changes if item.kind == observe.FOLLOW)
    print(
        f"Declarations observed in {directory}: {reference} new reference(s), "
        f"{followed} written by a screen, {len(records)} edited by hand"
    )
    for record in records:
        print(f"  ! {record['name']} edited by hand (previous kept: {record['copy']})")
    for problem in problems:
        print(f"  ? {problem}")


if __name__ == "__main__":
    main()
