from __future__ import annotations

import sys
from pathlib import Path

from aistack.config import configured
from aistack.explications.from_ai_reasoning import import_explain_answers
from aistack.explications.from_pra_tests import import_pra_tests_comments
from aistack.hosts.records import load_hosts_declaration, read_all
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


def main() -> None:
    """
    Rebuild the Time Machine's graph from the data directory (ADR-0011 § 1 and 10).

    A full rebuild every time, never incremental. The optional argument is
    the data directory; the store lives at `<dir>/timemachine/graph`.
    AI `explain` answers and dated `pra_tests.yml` comments are first
    imported as Proposed Explications (each importer skips what it already
    recorded). Projections then run in order on the same store: links
    such as upgrade correlations come after the streams they connect,
    collection gaps after every stream's activity node exists, and dock
    changes after the Explications they link to.

    `pyoxigraph.Store` creates only the leaf directory, not its parents,
    hence the `mkdir(parents=True)`.
    """

    generated_dir = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GENERATED_DIR
    )
    store_path = generated_dir / "timemachine" / "graph"
    store_path.mkdir(parents=True, exist_ok=True)

    explications_dir = generated_dir / "explications"
    explain_import = import_explain_answers(generated_dir / "ai-reasoning", explications_dir)
    pra_tests = configured(Path(__file__).resolve().parents[1] / "pra" / "definitions" / "pra_tests.yml")
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
    upgrade_correlation_summary = project_upgrade_correlation(store, generated_dir=generated_dir)
    collection_gaps_summary = project_collection_gaps(store, generated_dir=generated_dir)
    dock_changes_summary = project_dock_changes(store, generated_dir=generated_dir)
    host_records = read_all(load_hosts_declaration(generated_dir))
    host_changes_summary = project_host_changes(store, host_records)

    print("Time Machine Projection")
    print(f"- Source: {generated_dir}")
    print(f"- Store: {store_path}")
    print(f"- Streams seen: {summary.streams_seen}")
    print(f"- Observations seen: {summary.observations_seen}")
    print(f"- Explications imported from AI answers: {explain_import.explications_recorded}")
    print(f"- Explications imported from pra_tests.yml: {pra_recorded}")
    print(f"- Explication subjects seen: {explications_summary.subjects_seen}")
    print(f"- Explications seen: {explications_summary.explications_seen}")
    print(f"- Docker-events batches seen: {docker_events_summary.batches_seen}")
    print(f"- Docker events seen: {docker_events_summary.events_seen}")
    print(f"- Docker-diff subjects seen: {docker_diff_summary.subjects_seen}")
    print(f"- Docker-diff snapshots seen: {docker_diff_summary.snapshots_seen}")
    print(f"- Docker-digest subjects seen: {docker_digest_summary.subjects_seen}")
    print(f"- Docker-digest observations seen: {docker_digest_summary.snapshots_seen}")
    print(f"- Docker-packages subjects seen: {docker_packages_summary.subjects_seen}")
    print(f"- Docker-packages observations seen: {docker_packages_summary.snapshots_seen}")
    print(f"- Upgrade-correlation subjects seen: {upgrade_correlation_summary.subjects_seen}")
    print(f"- Digest changes seen: {upgrade_correlation_summary.digest_changes_seen}")
    print(f"- Upgrade correlations written: {upgrade_correlation_summary.correlations_written}")
    print(f"- Collection-gap streams seen: {collection_gaps_summary.streams_seen}")
    print(f"- Collection gaps seen: {collection_gaps_summary.gaps_seen}")
    print(f"- Governed changes seen: {dock_changes_summary.changes_seen}")
    print(f"- Hosts seen: {host_changes_summary.hosts_seen} ({host_changes_summary.hosts_unreadable} unreadable)")
    print(f"- Host events seen: {host_changes_summary.events_seen}")
    for records in host_records:
        if records.problem:
            print(f"  ! {records.host}: {records.problem}")
    print(
        "- Facts written: "
        f"{summary.facts_written + explications_summary.facts_written + docker_events_summary.facts_written + docker_diff_summary.facts_written + docker_digest_summary.facts_written + docker_packages_summary.facts_written + upgrade_correlation_summary.facts_written + collection_gaps_summary.facts_written + dock_changes_summary.facts_written + host_changes_summary.facts_written}"
    )
    print(
        "- Facts dropped: "
        f"{summary.facts_dropped + explications_summary.facts_dropped + docker_events_summary.facts_dropped + docker_diff_summary.facts_dropped + docker_digest_summary.facts_dropped + docker_packages_summary.facts_dropped + upgrade_correlation_summary.facts_dropped + collection_gaps_summary.facts_dropped + dock_changes_summary.facts_dropped + host_changes_summary.facts_dropped}"
    )


if __name__ == "__main__":
    main()
