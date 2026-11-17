from __future__ import annotations

import sys
import uuid
from pathlib import Path

from aistack.kernel.runtime import KernelRuntime, Request
from aistack.kernel.tracing import FileTraceRepository
from aistack.tasks.timemachine_rebuild import TimeMachineRebuildTask
from aistack.timemachine.projection import DEFAULT_GENERATED_DIR


def main() -> None:
    """
    Rebuild the Time Machine's graph from the data directory (ADR-0011 § 1 and 10).

    The Runtime executes the `timemachine.rebuild` Task (ADR-0027 § 10).
    The optional argument is the data directory; the store lives at
    `<dir>/timemachine/graph` and the trace of the run beside the other
    streams, under `<dir>/history/execution-trace/`: the data directory
    is the one the graph is rebuilt from, not necessarily the working
    directory's.
    """

    generated_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GENERATED_DIR

    runtime = KernelRuntime.boot(
        trace_repository=FileTraceRepository(output_path=generated_dir / "execution-trace.json")
    )

    request = Request(
        request_id=str(uuid.uuid4()),
        task_id=TimeMachineRebuildTask.task_id,
        payload={"generated_dir": str(generated_dir)},
    )

    data = runtime.execute(request).observation.data

    print("Time Machine Projection")
    print(f"- Source: {data['source']}")
    print(f"- Store: {data['store']}")
    print(f"- Streams seen: {data['streams_seen']}")
    print(f"- Observations seen: {data['observations_seen']}")
    print(f"- Explications imported from AI answers: {data['explications_from_ai_answers']}")
    print(f"- Explications imported from pra_tests.yml: {data['explications_from_pra_tests']}")
    print(f"- Explication subjects seen: {data['explication_subjects_seen']}")
    print(f"- Explications seen: {data['explications_seen']}")
    print(f"- Docker-events batches seen: {data['docker_events_batches_seen']}")
    print(f"- Docker events seen: {data['docker_events_seen']}")
    print(f"- Docker-diff subjects seen: {data['docker_diff_subjects_seen']}")
    print(f"- Docker-diff snapshots seen: {data['docker_diff_snapshots_seen']}")
    print(f"- Docker-digest subjects seen: {data['docker_digest_subjects_seen']}")
    print(f"- Docker-digest observations seen: {data['docker_digest_observations_seen']}")
    print(f"- Docker-packages subjects seen: {data['docker_packages_subjects_seen']}")
    print(f"- Docker-packages observations seen: {data['docker_packages_observations_seen']}")
    print(f"- Upgrade-correlation subjects seen: {data['upgrade_correlation_subjects_seen']}")
    print(f"- Digest changes seen: {data['digest_changes_seen']}")
    print(f"- Upgrade correlations written: {data['upgrade_correlations_written']}")
    print(f"- Collection-gap streams seen: {data['collection_gap_streams_seen']}")
    print(f"- Collection gaps seen: {data['collection_gaps_seen']}")
    print(f"- Governed changes seen: {data['governed_changes_seen']}")
    print(f"- Hosts seen: {data['hosts_seen']} ({data['hosts_unreadable']} unreadable)")
    print(f"- Host events seen: {data['host_events_seen']}")
    for problem in data["host_problems"]:
        print(f"  ! {problem}")
    print(f"- Facts written: {data['facts_written']}")
    print(f"- Facts dropped: {data['facts_dropped']}")


if __name__ == "__main__":
    main()
