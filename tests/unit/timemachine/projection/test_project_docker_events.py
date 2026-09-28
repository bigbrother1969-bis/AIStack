"""
`aistack.timemachine.projection.project_docker_events` — against a
real batch recorded through `aistack.providers.docker.events_history
.record_docker_events`, the same "no mocks, real producer" discipline
`test_project_explications.py`/`test_project_observation_history.py`
already hold for the other streams.
"""

from __future__ import annotations

from pathlib import Path

from aistack.providers.docker.events_history import record_docker_events
from aistack.timemachine.iri import stream_iri
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_docker_events
from aistack.timemachine.vocabulary import (
    AISTACK_DOCKER_ACTION,
    AISTACK_OCCURRED_AT,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_ENTITY,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
)

ONE_EVENT = [
    {
        "subject": "aistack/aistack-core",
        "occurred_at": "2026-09-28T10:00:05.123456+00:00",
        "action": "start",
        "raw": {"Type": "container", "Action": "start"},
    }
]


def test_no_batches_recorded_produces_nothing(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    generated_dir.mkdir(parents=True)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_events(store, generated_dir=generated_dir)

    assert summary.batches_seen == 0
    assert summary.events_seen == 0
    assert summary.facts_written == 0


def test_an_event_is_projected_as_its_own_entity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_events(
        ONE_EVENT,
        since="2026-09-28T10:00:00Z",
        until="2026-09-28T10:00:10Z",
        output_path=generated_dir / "docker-events" / "docker-events.json",
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_events(store, generated_dir=generated_dir)

    assert summary.batches_seen == 1
    assert summary.events_seen == 1

    entities = list(store.query(f"SELECT ?s WHERE {{ ?s <{RDF_TYPE}> <{PROV_ENTITY}> }}"))
    assert len(entities) == 1


def test_an_event_carries_its_stable_subject_action_and_occurred_at(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_events(
        ONE_EVENT,
        since="S",
        until="U",
        output_path=generated_dir / "docker-events" / "docker-events.json",
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_events(store, generated_dir=generated_dir)

    subjects = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_STABLE_SUBJECT}> ?o }}"))
    assert subjects == [{"o": "aistack/aistack-core"}]

    actions = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_DOCKER_ACTION}> ?o }}"))
    assert actions == [{"o": "start"}]

    # Oxigraph's own `xsd:dateTime` canonical form uses the `Z` suffix
    # for UTC, not `+00:00` — a round-trip fact, not this module's own
    # choice; `ONE_EVENT`'s content is written with `+00:00`.
    occurred = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_OCCURRED_AT}> ?o }}"))
    assert occurred == [{"o": "2026-09-28T10:00:05.123456Z"}]


def test_an_event_is_generated_by_the_shared_docker_events_activity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_events(
        ONE_EVENT,
        since="S",
        until="U",
        output_path=generated_dir / "docker-events" / "docker-events.json",
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_events(store, generated_dir=generated_dir)

    activity = stream_iri("docker-events")
    generated_by = list(
        store.query(f"SELECT ?o WHERE {{ ?s <{PROV_WAS_GENERATED_BY}> ?o }}")
    )
    assert generated_by == [{"o": activity}]

    activity_types = list(
        store.query(f"SELECT ?t WHERE {{ <{activity}> <{RDF_TYPE}> ?t }}")
    )
    assert activity_types == [{"t": PROV_ACTIVITY}]


def test_two_events_in_one_batch_each_get_their_own_entity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    two_events = ONE_EVENT + [
        {
            "subject": "some-other-service",
            "occurred_at": "2026-09-28T10:00:06Z",
            "action": "destroy",
            "raw": {},
        }
    ]
    record_docker_events(
        two_events,
        since="S",
        until="U",
        output_path=generated_dir / "docker-events" / "docker-events.json",
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_events(store, generated_dir=generated_dir)

    assert summary.events_seen == 2
    entities = list(store.query(f"SELECT ?s WHERE {{ ?s <{RDF_TYPE}> <{PROV_ENTITY}> }}"))
    assert len(entities) == 2


def test_the_generic_observation_history_walk_never_sees_this_stream(tmp_path: Path):
    """
    `aistack.providers.docker.events_history.DEFAULT_OUTPUT_PATH`
    deliberately lives off `generated_dir`'s own flat `history/` root
    — `aistack.timemachine.projection.project_observation_history`'s
    own `available_stems(generated_dir)` walk must never find it, or
    the same batch would be projected twice under two different fact
    models.
    """
    from aistack.history import available_stems

    generated_dir = tmp_path / "reports" / "generated"
    record_docker_events(
        ONE_EVENT,
        since="S",
        until="U",
        output_path=generated_dir / "docker-events" / "docker-events.json",
    )

    assert "docker-events" not in available_stems(generated_dir)
