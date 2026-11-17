from __future__ import annotations

from pathlib import Path

from aistack.config import configured
from aistack.explications.from_ai_reasoning import import_explain_answers
from aistack.explications.from_pra_tests import import_pra_tests_comments
from aistack.hosts.records import load_hosts_declaration, read_all
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import (
    DEFAULT_GENERATED_DIR,
    project_collection_gaps,
    project_dock_changes,
    project_docker_diff,
    project_docker_digest,
    project_docker_events,
    project_docker_packages,
    project_explications,
    project_host_changes,
    project_observation_history,
    project_upgrade_correlation,
)


class TimeMachineRebuildTask:
    """
    Rebuild the Time Machine's graph from the data directory
    (`timemachine.rebuild`, ADR-0011 § 1 and 10, ADR-0027 § 10).

    The fourth chain the Runtime executes. A full rebuild every time,
    never incremental. The request payload's `generated_dir` (default
    `DEFAULT_GENERATED_DIR`) is the data directory; the store lives at
    `<dir>/timemachine/graph`. AI `explain` answers and dated
    `pra_tests.yml` comments are first imported as Proposed Explications
    (each importer skips what it already recorded). Projections then run
    in order on the same store: links such as upgrade correlations come
    after the streams they connect, collection gaps after every stream's
    activity node exists, and dock changes after the Explications they
    link to.

    `pyoxigraph.Store` creates only the leaf directory, not its parents,
    hence the `mkdir(parents=True)`.

    The Task reads no provider: what it rebuilds from is on disk. Returns
    an Observation of plain values, one per figure the command reports.
    """

    task_id = "timemachine.rebuild"
    task_name = "Time Machine rebuild"

    def execute(self, request: Request) -> Observation:
        generated_dir = Path(request.payload.get("generated_dir", str(DEFAULT_GENERATED_DIR)))
        store_path = generated_dir / "timemachine" / "graph"
        store_path.mkdir(parents=True, exist_ok=True)

        explications_dir = generated_dir / "explications"
        explain_import = import_explain_answers(generated_dir / "ai-reasoning", explications_dir)
        pra_tests = configured(
            Path(__file__).resolve().parents[1] / "pra" / "definitions" / "pra_tests.yml"
        )
        pra_recorded = (
            import_pra_tests_comments(pra_tests, explications_dir).explications_recorded
            if pra_tests.is_file()
            else 0
        )

        store = OxigraphGraphStore(store_path)
        summary = project_observation_history(store, generated_dir=generated_dir)
        explications_summary = project_explications(store, generated_dir=generated_dir)
        docker_events_summary = project_docker_events(store, generated_dir=generated_dir)
        docker_diff_summary = project_docker_diff(store, generated_dir=generated_dir)
        docker_digest_summary = project_docker_digest(store, generated_dir=generated_dir)
        docker_packages_summary = project_docker_packages(store, generated_dir=generated_dir)
        upgrade_correlation_summary = project_upgrade_correlation(
            store, generated_dir=generated_dir
        )
        collection_gaps_summary = project_collection_gaps(store, generated_dir=generated_dir)
        dock_changes_summary = project_dock_changes(store, generated_dir=generated_dir)
        host_records = read_all(load_hosts_declaration(generated_dir))
        host_changes_summary = project_host_changes(store, host_records)

        summaries = (
            summary,
            explications_summary,
            docker_events_summary,
            docker_diff_summary,
            docker_digest_summary,
            docker_packages_summary,
            upgrade_correlation_summary,
            collection_gaps_summary,
            dock_changes_summary,
            host_changes_summary,
        )

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={
                "source": str(generated_dir),
                "store": str(store_path),
                "streams_seen": summary.streams_seen,
                "observations_seen": summary.observations_seen,
                "explications_from_ai_answers": explain_import.explications_recorded,
                "explications_from_pra_tests": pra_recorded,
                "explication_subjects_seen": explications_summary.subjects_seen,
                "explications_seen": explications_summary.explications_seen,
                "docker_events_batches_seen": docker_events_summary.batches_seen,
                "docker_events_seen": docker_events_summary.events_seen,
                "docker_diff_subjects_seen": docker_diff_summary.subjects_seen,
                "docker_diff_snapshots_seen": docker_diff_summary.snapshots_seen,
                "docker_digest_subjects_seen": docker_digest_summary.subjects_seen,
                "docker_digest_observations_seen": docker_digest_summary.snapshots_seen,
                "docker_packages_subjects_seen": docker_packages_summary.subjects_seen,
                "docker_packages_observations_seen": docker_packages_summary.snapshots_seen,
                "upgrade_correlation_subjects_seen": upgrade_correlation_summary.subjects_seen,
                "digest_changes_seen": upgrade_correlation_summary.digest_changes_seen,
                "upgrade_correlations_written": upgrade_correlation_summary.correlations_written,
                "collection_gap_streams_seen": collection_gaps_summary.streams_seen,
                "collection_gaps_seen": collection_gaps_summary.gaps_seen,
                "governed_changes_seen": dock_changes_summary.changes_seen,
                "hosts_seen": host_changes_summary.hosts_seen,
                "hosts_unreadable": host_changes_summary.hosts_unreadable,
                "host_events_seen": host_changes_summary.events_seen,
                "host_problems": [
                    f"{records.host}: {records.problem}"
                    for records in host_records
                    if records.problem
                ],
                "facts_written": sum(item.facts_written for item in summaries),
                "facts_dropped": sum(item.facts_dropped for item in summaries),
            },
        )
