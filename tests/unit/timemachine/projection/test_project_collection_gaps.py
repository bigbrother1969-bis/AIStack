"""
`aistack.timemachine.projection.project_collection_gaps` — against a
real gap recorded through `aistack.generators.collection_gap
.record_collection_gap`, the same "no mocks, real producer"
discipline `test_project_docker_events.py` already holds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aistack.generators.collection_gap import record_collection_gap
from aistack.timemachine.iri import stream_iri
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_collection_gaps
from aistack.timemachine.vocabulary import (
    AISTACK_COLLECTION_GAP,
    AISTACK_OCCURRED_AT,
    AISTACK_STABLE_SUBJECT,
    PROV_ENTITY,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
)


def _record_gap(generated_dir: Path) -> None:
    record_collection_gap(
        "docker-events",
        checkpoint_until="2026-09-28T10:00:00+00:00",
        now=datetime(2026, 9, 28, 10, 5, 0, tzinfo=timezone.utc),
        generated_dir=generated_dir,
    )


def test_no_root_at_all_produces_nothing(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    generated_dir.mkdir(parents=True)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_collection_gaps(store, generated_dir=generated_dir)

    assert summary.streams_seen == 0
    assert summary.gaps_seen == 0
    assert summary.facts_written == 0


def test_a_recorded_gap_is_projected_as_its_own_entity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    _record_gap(generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_collection_gaps(store, generated_dir=generated_dir)

    assert summary.streams_seen == 1
    assert summary.gaps_seen == 1
    entities = list(store.query(f"SELECT ?s WHERE {{ ?s <{RDF_TYPE}> <{PROV_ENTITY}> }}"))
    assert len(entities) == 1


def test_a_gap_carries_its_start_and_its_stream_as_subject(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    _record_gap(generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_collection_gaps(store, generated_dir=generated_dir)

    occurred = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_OCCURRED_AT}> ?o }}"))
    assert occurred == [{"o": "2026-09-28T10:00:00Z"}]

    subjects = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_STABLE_SUBJECT}> ?o }}"))
    assert subjects == [{"o": "docker-events"}]


def test_the_stream_s_own_activity_links_to_the_gap(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    _record_gap(generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_collection_gaps(store, generated_dir=generated_dir)

    activity = stream_iri("docker-events")
    linked = list(
        store.query(f"SELECT ?o WHERE {{ <{activity}> <{AISTACK_COLLECTION_GAP}> ?o }}")
    )
    assert len(linked) == 1

    generated_by = list(
        store.query(f"SELECT ?o WHERE {{ ?s <{PROV_WAS_GENERATED_BY}> ?o }}")
    )
    assert generated_by == [{"o": activity}]


def test_two_streams_each_get_their_own_gap(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    now = datetime(2026, 9, 28, 10, 5, 0, tzinfo=timezone.utc)
    record_collection_gap(
        "docker-events", checkpoint_until="2026-09-28T10:00:00+00:00", now=now, generated_dir=generated_dir
    )
    record_collection_gap(
        "docker-diff", checkpoint_until="2026-09-28T09:50:00+00:00", now=now, generated_dir=generated_dir
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_collection_gaps(store, generated_dir=generated_dir)

    assert summary.streams_seen == 2
    assert summary.gaps_seen == 2
