from __future__ import annotations

from datetime import UTC, datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.explications.store import (
    deserialize_explication,
    explication_history_path,
    read_latest_explication,
    record_explication,
    serialize_explication,
)


def _artifact(**overrides: object) -> KnowledgeArtifact:
    """
    A real `KnowledgeArtifact`, not a fabricated one — every mandatory
    field the contract requires is given a real, honest value. It is
    a test fixture, not a stand-in for a real imported source: no
    importer exists yet (patch 2's concern, `ADR-0011` § 8), so its
    `source` says exactly that rather than pretending to be a commit
    or an `explain` answer.
    """

    fields: dict[str, object] = {
        "id": "test-subject",
        "title": "A test Explication",
        "declared_type": "Explication",
        "domain": UNDECLARED,
        "semantic_type": UNDECLARED,
        "criticality": UNDECLARED,
        "owner": UNDECLARED,
        "source": "test:aistack.explications.store",
        "created_at": datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC),
        "confidence": "Proposed",
        "status": UNDECLARED,
        "content": "This is what the test explains.",
    }
    fields.update(overrides)
    return KnowledgeArtifact(**fields)  # type: ignore[arg-type]


def test_serialize_then_deserialize_round_trips_every_field():
    artifact = _artifact()

    restored = deserialize_explication(serialize_explication(artifact))

    assert restored == artifact


def test_record_explication_writes_the_stable_latest_path(tmp_path):
    artifact = _artifact()

    latest_path = record_explication(artifact, output_dir=tmp_path)

    assert latest_path == explication_history_path(artifact.id, tmp_path)
    assert latest_path.exists()


def test_record_explication_keeps_every_version_in_history(tmp_path):
    first = _artifact(content="first version")
    record_explication(first, output_dir=tmp_path)

    second = _artifact(
        content="a correction to the first version",
        updated_at=datetime(2026, 9, 27, 13, 0, 0, tzinfo=UTC),
    )
    record_explication(second, output_dir=tmp_path)

    history_dir = tmp_path / "history" / "test-subject"
    assert len(list(history_dir.iterdir())) == 2

    current = read_latest_explication("test-subject", output_dir=tmp_path)
    assert current == second


def test_read_latest_explication_on_a_never_recorded_subject_returns_none(tmp_path):
    assert read_latest_explication("never-recorded", output_dir=tmp_path) is None


def test_three_versions_written_in_one_second_are_all_read_back(tmp_path, monkeypatch):
    # The defect deferred to 1.9: an importer writing several versions of
    # one subject in the same second used to read back as one.
    from aistack.explications.store import read_explication_history

    monkeypatch.setattr(
        "aistack.generators.history.wall_clock", lambda: datetime(2026, 10, 5, 9, 0, 0, tzinfo=UTC)
    )
    for text in ("one", "two", "three"):
        record_explication(_artifact(content=text), output_dir=tmp_path)

    assert [artifact.content for artifact in read_explication_history("test-subject", tmp_path)] == [
        "one",
        "two",
        "three",
    ]
