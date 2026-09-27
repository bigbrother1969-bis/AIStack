"""
`aistack.timemachine.projection.project_explications` — against a
real `KnowledgeArtifact` recorded through
`aistack.explications.record_explication`, the same "no mocks, real
producer" discipline `test_project_observation_history.py` already
holds for the four existing streams.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.explications import record_explication
from aistack.timemachine.iri import agent_iri, subject_iri
from aistack.timemachine.oxigraph_store import OxigraphGraphStore
from aistack.timemachine.projection import project_explications
from aistack.timemachine.vocabulary import (
    AISTACK_CONFIDENCE,
    AISTACK_EXPLAINS,
    AISTACK_EXPLICATION_STATUS,
    PROV_ENTITY,
    PROV_WAS_ATTRIBUTED_TO,
    RDF_TYPE,
)


def _artifact(**overrides: object) -> KnowledgeArtifact:
    fields: dict[str, object] = dict(
        id="booklore_db",
        title="Explication : booklore_db",
        declared_type="Explication",
        domain=UNDECLARED,
        semantic_type=UNDECLARED,
        criticality=UNDECLARED,
        owner=UNDECLARED,
        source="model:mistral",
        created_at=datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC),
        updated_at=datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC),
        confidence="Proposed",
        status=UNDECLARED,
        content="booklore_db runs hot because of X.",
        metadata={
            "source_stream": "ai-reasoning",
            "source_instant": "2026-09-27T12-00-00Z",
            "explication_status": "Proposed",
        },
    )
    fields.update(overrides)
    return KnowledgeArtifact(**fields)  # type: ignore[arg-type]


def test_an_explication_is_projected_as_an_entity_that_explains_its_subject(
    tmp_path: Path,
):
    generated_dir = tmp_path / "reports" / "generated"
    record_explication(_artifact(), output_dir=generated_dir / "explications")

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_explications(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 1
    assert summary.explications_seen == 1

    rows = list(
        store.query(
            "SELECT ?o WHERE { "
            f"?entity <{AISTACK_EXPLAINS}> ?o }}"
        )
    )
    assert rows == [{"o": subject_iri("booklore_db")}]


def test_an_explication_carries_its_confidence_and_status(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_explication(_artifact(), output_dir=generated_dir / "explications")

    store = OxigraphGraphStore(tmp_path / "graph")
    project_explications(store, generated_dir=generated_dir)

    confidences = list(store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_CONFIDENCE}> ?o }}"))
    assert confidences == [{"o": "Proposed"}]

    statuses = list(
        store.query(f"SELECT ?o WHERE {{ ?s <{AISTACK_EXPLICATION_STATUS}> ?o }}")
    )
    assert statuses == [{"o": "Proposed"}]


def test_an_explication_is_attributed_to_its_source_as_an_agent(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    record_explication(_artifact(), output_dir=generated_dir / "explications")

    store = OxigraphGraphStore(tmp_path / "graph")
    project_explications(store, generated_dir=generated_dir)

    rows = list(
        store.query(f"SELECT ?o WHERE {{ ?s <{PROV_WAS_ATTRIBUTED_TO}> ?o }}")
    )
    assert rows == [{"o": agent_iri("model:mistral")}]

    agent_types = list(
        store.query(
            f"SELECT ?t WHERE {{ <{agent_iri('model:mistral')}> <{RDF_TYPE}> ?t }}"
        )
    )
    assert len(agent_types) == 1


def test_a_correction_adds_a_second_explication_entity_not_a_replacement(
    tmp_path: Path, monkeypatch
):
    """
    Two real writes a second apart, not two writes in the same
    process tick — `available_instants` deliberately collapses
    same-second writes to one historical moment
    (`aistack.history.query`'s own docstring), so the clock is
    controlled here the same way
    `tests/unit/generators/test_history.py
    ::test_two_writes_in_the_same_second_both_survive` controls it to
    test the opposite case.
    """

    import aistack.generators.history as history_module

    class FrozenDatetime(history_module.datetime):
        _instant = datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls._instant

    monkeypatch.setattr(history_module, "datetime", FrozenDatetime)

    generated_dir = tmp_path / "reports" / "generated"
    FrozenDatetime._instant = datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)
    record_explication(_artifact(content="first"), output_dir=generated_dir / "explications")

    FrozenDatetime._instant = datetime(2026, 9, 27, 13, 0, 0, tzinfo=UTC)
    record_explication(
        _artifact(
            content="a correction",
            created_at=datetime(2026, 9, 27, 13, 0, 0, tzinfo=UTC),
            metadata={
                "source_stream": "ai-reasoning",
                "source_instant": "2026-09-27T13-00-00Z",
                "explication_status": "Proposed",
            },
        ),
        output_dir=generated_dir / "explications",
    )

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_explications(store, generated_dir=generated_dir)

    assert summary.explications_seen == 2
    entities = list(store.query(f"SELECT ?s WHERE {{ ?s <{RDF_TYPE}> <{PROV_ENTITY}> }}"))
    assert len(entities) == 2


def test_no_explications_recorded_produces_nothing(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    generated_dir.mkdir(parents=True)

    store = OxigraphGraphStore(tmp_path / "graph")
    summary = project_explications(store, generated_dir=generated_dir)

    assert summary.subjects_seen == 0
    assert summary.explications_seen == 0
    assert summary.facts_written == 0
