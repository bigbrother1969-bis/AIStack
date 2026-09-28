"""
`aistack.timemachine.projection.project_docker_diff` — against real
snapshots recorded through `aistack.providers.docker.diff_history
.record_docker_diff`, the same "no mocks, real producer" discipline
`test_project_docker_events.py` already holds.
"""

from __future__ import annotations

from pathlib import Path

from aistack.providers.docker.diff_history import record_docker_diff
from aistack.timemachine.iri import stream_iri
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_docker_diff
from aistack.timemachine.vocabulary import (
    AISTACK_CHANGE_COUNT,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_ENTITY,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
)

ONE_CHANGE = [{"kind": "A", "path": "/run/nginx.pid"}]
TWO_CHANGES = [
    {"kind": "A", "path": "/run/nginx.pid"},
    {"kind": "C", "path": "/etc/hosts"},
]


def test_no_root_at_all_produces_nothing(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    generated_dir.mkdir(parents=True)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_diff(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 0
    assert summary.snapshots_seen == 0
    assert summary.facts_written == 0


def test_a_recorded_snapshot_is_projected_as_its_own_entity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_diff(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    assert summary.snapshots_seen == 1
    entities = list(store.query(f"SELECT ?s WHERE {{ ?s <{RDF_TYPE}> <{PROV_ENTITY}> }}"))
    assert len(entities) == 1


def test_a_subject_whose_name_embeds_a_slash_is_correctly_rebuilt(tmp_path: Path):
    """
    `arrstack/gluetun` nests two directories deep on disk
    (`aistack.providers.docker.diff_history._output_path`'s own
    docstring) — this asserts the projector's own walk reverses that
    nesting back into the exact original subject string, not
    `"arrstack"` or `"gluetun"` alone.
    """
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_diff(store, generated_dir=generated_dir)

    subjects = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_STABLE_SUBJECT}> ?o }}"))
    assert subjects == [{"o": "arrstack/gluetun"}]


def test_a_subject_with_no_slash_is_also_found(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("frigate", ONE_CHANGE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_diff(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    subjects = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_STABLE_SUBJECT}> ?o }}"))
    assert subjects == [{"o": "frigate"}]


def test_a_snapshot_carries_its_own_change_count(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("frigate", TWO_CHANGES, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_diff(store, generated_dir=generated_dir)

    counts = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_CHANGE_COUNT}> ?o }}"))
    assert counts == [{"o": "2"}]


def test_an_empty_snapshot_still_gets_a_zero_change_count(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("frigate", [], generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_diff(store, generated_dir=generated_dir)

    counts = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_CHANGE_COUNT}> ?o }}"))
    assert counts == [{"o": "0"}]


def test_a_snapshot_is_generated_by_the_shared_docker_diff_activity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("frigate", ONE_CHANGE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_diff(store, generated_dir=generated_dir)

    activity = stream_iri("docker-diff")
    generated_by = list(
        store.query(f"SELECT ?o WHERE {{ ?s <{PROV_WAS_GENERATED_BY}> ?o }}")
    )
    assert generated_by == [{"o": activity}]

    activity_types = list(
        store.query(f"SELECT ?t WHERE {{ <{activity}> <{RDF_TYPE}> ?t }}")
    )
    assert activity_types == [{"t": PROV_ACTIVITY}]


def test_two_write_on_change_snapshots_for_one_subject_each_get_their_own_entity(
    tmp_path: Path, monkeypatch
):
    """
    Two real writes a second apart, not two calls inside the same
    wall-clock second — `aistack.generators.history
    .write_artifact_with_history`'s own collision suffix keeps both
    files on disk either way, but `aistack.history.query
    .available_instants`'s own docstring is explicit that same-second
    writes "collapse to one instant" there; frozen a second apart is
    what actually exercises two distinct snapshots for one subject.
    """
    import aistack.generators.history as history_module

    generated_dir = tmp_path / "reports" / "generated"

    class FrozenAt10_00_00(history_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 28, 10, 0, 0, tzinfo=tz)

    class FrozenAt10_00_01(history_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 9, 28, 10, 0, 1, tzinfo=tz)

    monkeypatch.setattr(history_module, "datetime", FrozenAt10_00_00)
    record_docker_diff("frigate", ONE_CHANGE, generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", FrozenAt10_00_01)
    record_docker_diff("frigate", TWO_CHANGES, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_diff(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    assert summary.snapshots_seen == 2


def test_two_different_subjects_each_get_their_own_entity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("arrstack/gluetun", ONE_CHANGE, generated_dir=generated_dir)
    record_docker_diff("frigate", TWO_CHANGES, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_diff(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 2
    assert summary.snapshots_seen == 2


def test_the_generic_observation_history_walk_never_sees_this_stream(tmp_path: Path):
    from aistack.history import available_stems

    generated_dir = tmp_path / "reports" / "generated"
    record_docker_diff("frigate", ONE_CHANGE, generated_dir=generated_dir)

    assert "docker-diff" not in available_stems(generated_dir)
