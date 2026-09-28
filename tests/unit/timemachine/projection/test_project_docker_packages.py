"""
`aistack.timemachine.projection.project_docker_packages` — against
real observations recorded through `aistack.providers.docker
.packages_history.record_package_inventory`, the same "no mocks, real
producer" discipline `test_project_docker_digest.py` already holds.
"""

from __future__ import annotations

from pathlib import Path

from aistack.providers.docker.packages_history import record_package_inventory
from aistack.timemachine.iri import stream_iri
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_docker_packages
from aistack.timemachine.vocabulary import (
    AISTACK_PACKAGE_COUNT,
    AISTACK_PACKAGE_MECHANISM,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_ENTITY,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
)

PACKAGES_ONE = [
    {"name": "bash", "version": "5.2.15-2+b7"},
    {"name": "curl", "version": "7.88.1-10"},
]
PACKAGES_TWO = [{"name": "curl", "version": "7.90.0-1"}]


def test_no_root_at_all_produces_nothing(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    generated_dir.mkdir(parents=True)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_packages(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 0
    assert summary.snapshots_seen == 0
    assert summary.facts_written == 0


def test_a_recorded_observation_is_projected_as_its_own_entity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory(
        "arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_packages(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    assert summary.snapshots_seen == 1
    entities = list(store.query(f"SELECT ?s WHERE {{ ?s <{RDF_TYPE}> <{PROV_ENTITY}> }}"))
    assert len(entities) == 1


def test_a_subject_whose_name_embeds_a_slash_is_correctly_rebuilt(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory(
        "arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_packages(store, generated_dir=generated_dir)

    subjects = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_STABLE_SUBJECT}> ?o }}"))
    assert subjects == [{"o": "arrstack/gluetun"}]


def test_a_subject_with_no_slash_is_also_found(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("frigate", "apk", PACKAGES_ONE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_packages(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    subjects = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_STABLE_SUBJECT}> ?o }}"))
    assert subjects == [{"o": "frigate"}]


def test_an_observation_carries_its_own_package_count(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_packages(store, generated_dir=generated_dir)

    counts = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_PACKAGE_COUNT}> ?o }}"))
    assert counts == [{"o": "2"}]


def test_an_observation_carries_its_own_mechanism(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("frigate", "apk", PACKAGES_ONE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_packages(store, generated_dir=generated_dir)

    mechanisms = list(
        store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_PACKAGE_MECHANISM}> ?o }}")
    )
    assert mechanisms == [{"o": "apk"}]


def test_an_empty_inventory_is_still_a_real_observation_with_count_zero(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("frigate", "none", [], generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_packages(store, generated_dir=generated_dir)

    assert summary.snapshots_seen == 1
    counts = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_PACKAGE_COUNT}> ?o }}"))
    assert counts == [{"o": "0"}]


def test_an_observation_is_generated_by_the_shared_docker_packages_activity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    project_docker_packages(store, generated_dir=generated_dir)

    activity = stream_iri("docker-packages")
    generated_by = list(
        store.query(f"SELECT ?o WHERE {{ ?s <{PROV_WAS_GENERATED_BY}> ?o }}")
    )
    assert generated_by == [{"o": activity}]

    activity_types = list(
        store.query(f"SELECT ?t WHERE {{ <{activity}> <{RDF_TYPE}> ?t }}")
    )
    assert activity_types == [{"t": PROV_ACTIVITY}]


def test_two_write_on_change_observations_for_one_subject_each_get_their_own_entity(
    tmp_path: Path, monkeypatch
):
    """
    Two real writes a second apart, the same reasoning
    `test_project_docker_digest.py`'s own equivalent test already
    gives (`aistack.history.query.available_instants`'s own docstring
    is explicit that same-second writes collapse to one instant
    there).
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
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    monkeypatch.setattr(history_module, "datetime", FrozenAt10_00_01)
    record_package_inventory("frigate", "dpkg", PACKAGES_TWO, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_packages(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    assert summary.snapshots_seen == 2


def test_two_different_subjects_each_get_their_own_entity(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory(
        "arrstack/gluetun", "dpkg", PACKAGES_ONE, generated_dir=generated_dir
    )
    record_package_inventory("frigate", "apk", PACKAGES_TWO, generated_dir=generated_dir)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_docker_packages(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 2
    assert summary.snapshots_seen == 2


def test_the_generic_observation_history_walk_never_sees_this_stream(tmp_path: Path):
    from aistack.history import available_stems

    generated_dir = tmp_path / "reports" / "generated"
    record_package_inventory("frigate", "dpkg", PACKAGES_ONE, generated_dir=generated_dir)

    assert "docker-packages" not in available_stems(generated_dir)
