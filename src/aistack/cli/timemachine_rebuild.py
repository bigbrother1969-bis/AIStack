from __future__ import annotations

import sys
from pathlib import Path

from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import (
    DEFAULT_GENERATED_DIR,
    project_collection_gaps,
    project_docker_diff,
    project_docker_digest,
    project_docker_events,
    project_docker_packages,
    project_explications,
    project_observation_history,
)


def main() -> None:
    """
    Rebuild the Time Machine's graph from whatever Observation
    History and Explications currently hold — `ADR-0011` § *Decision*
    1 and 10: a full rebuild every time, on demand, never incremental.

    The first real caller of `project_observation_history` —
    everything before this module was contract and mechanism with
    nothing to invoke it. `generated_dir` takes the one optional
    argument every other CLI in this package already accepts this
    way (`aistack.cli.knowledge_integrity`'s own bundle override);
    the store always lives at `<generated_dir>/timemachine/graph`,
    inside the same tree the four source streams already occupy and
    `.gitignore` already excludes wholesale (`FDN-0003`: a generated
    artifact is disposable, and the graph is one, exactly like the
    streams it is built from) — a second, separate directory for it
    would split one already-unified, already-governed disposable area
    into two for no real benefit.

    **`project_explications` runs second, against the same store,
    never clearing it again** — Explications is the fifth source
    stream `project_observation_history`'s own docstring already
    named ("soon five"), added to the one rebuild pass rather than a
    second, independent graph. It projects whatever
    `aistack.cli.explications_import` (or a sibling importer, still to
    come for the other three sources) has already recorded — this
    command never imports raw sources itself, only what Explications'
    own store already holds.

    **`project_docker_events` runs third, against the same store, for
    the same reason** — 1.5's first collector
    (`aistack.cli.docker_events_monitor`, cadrage 2026-09-28), a sixth
    source stream with its own dedicated projector (`aistack
    .timemachine.projection.docker_events`'s own docstring says why a
    dedicated one, not a branch inside the generic walk).

    **`project_docker_diff` runs fourth, against the same store, for
    the same reason** — 1.5's second collector
    (`aistack.cli.docker_diff_monitor`, cadrage 2026-09-28), a
    seventh source stream with its own dedicated projector
    (`aistack.timemachine.projection.docker_diff`'s own docstring
    says why a dedicated one, not a branch inside the generic walk —
    the same reasoning `project_docker_events` already gives).

    **`project_docker_digest` runs fifth, against the same store, for
    the same reason** — 1.5's third collector
    (`aistack.cli.docker_digest_monitor`, cadrage 2026-09-28), an
    eighth source stream with its own dedicated projector
    (`aistack.timemachine.projection.docker_digest`'s own docstring
    says why a dedicated one, not a branch inside the generic walk).

    **`project_docker_packages` runs sixth, against the same store,
    for the same reason** — 1.5's fourth and last named collector
    (`aistack.cli.docker_packages_monitor`, cadré 2026-09-28, deferred
    past 1.5.0 and shipped in 1.5.1), a ninth source stream with its
    own dedicated projector (`aistack.timemachine.projection
    .docker_packages`'s own docstring says why a dedicated one, not a
    branch inside the generic walk).

    **`project_collection_gaps` runs seventh, against the same store,
    last on purpose.** `ADR-0011` § 9 (R11), built 2026-09-28 as a
    mechanism shared by every 1.5 monitor rather than per-collector —
    it links a recorded gap to a stream's own activity node
    (`aistack.timemachine.iri.stream_iri`), which that stream's own
    pass (third, above, for docker-events; fourth, for docker-diff;
    fifth, for docker-digest; sixth, for docker-packages) is what
    actually creates as a `prov:Activity` fact. Running after every
    stream's own projection pass, in the same rebuild, means that node
    already exists by the time a gap tries to link to it, for every
    stream this rebuild knows how to project — never a second,
    competing activity node minted here for one this module does not
    own.

    **The leaf directory, created here, not assumed.** `pyoxigraph
    .Store`'s own documented behaviour creates the directory its
    `path` names if it is missing — measured, 2026-09-27, to create
    only that leaf, never its parents (`FileNotFoundError` on a
    freshly emptied tree otherwise, since `reports/generated/` itself
    may not exist yet on a host that has never run a provider
    generator). `mkdir(parents=True, exist_ok=True)` closes that gap
    before `OxigraphGraphStore` ever opens the store.
    """

    generated_dir = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_GENERATED_DIR
    )
    store_path = generated_dir / "timemachine" / "graph"
    store_path.mkdir(parents=True, exist_ok=True)

    store = OxigraphGraphStore(store_path)
    summary = project_observation_history(store, generated_dir=generated_dir)
    explications_summary = project_explications(store, generated_dir=generated_dir)
    docker_events_summary = project_docker_events(store, generated_dir=generated_dir)
    docker_diff_summary = project_docker_diff(store, generated_dir=generated_dir)
    docker_digest_summary = project_docker_digest(store, generated_dir=generated_dir)
    docker_packages_summary = project_docker_packages(store, generated_dir=generated_dir)
    collection_gaps_summary = project_collection_gaps(store, generated_dir=generated_dir)

    print("Time Machine Projection")
    print(f"- Source: {generated_dir}")
    print(f"- Store: {store_path}")
    print(f"- Streams seen: {summary.streams_seen}")
    print(f"- Observations seen: {summary.observations_seen}")
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
    print(f"- Collection-gap streams seen: {collection_gaps_summary.streams_seen}")
    print(f"- Collection gaps seen: {collection_gaps_summary.gaps_seen}")
    print(
        "- Facts written: "
        f"{summary.facts_written + explications_summary.facts_written + docker_events_summary.facts_written + docker_diff_summary.facts_written + docker_digest_summary.facts_written + docker_packages_summary.facts_written + collection_gaps_summary.facts_written}"
    )
    print(
        "- Facts dropped: "
        f"{summary.facts_dropped + explications_summary.facts_dropped + docker_events_summary.facts_dropped + docker_diff_summary.facts_dropped + docker_digest_summary.facts_dropped + docker_packages_summary.facts_dropped + collection_gaps_summary.facts_dropped}"
    )


if __name__ == "__main__":
    main()
