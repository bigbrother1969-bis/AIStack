"""
A person writes, validates or discards an Explication (`ADR-0015`):
every act one more version, the rules of who may confirm what, and the
history each form was drawn from.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.explications import record_explication
from aistack.explications.human import (
    DECLARED,
    DISCARDED,
    PROPOSED,
    VALIDATED,
    ExplicationChanged,
    ExplicationRefused,
    Person,
    discard,
    validate,
    versions,
    write,
)

ALICE = Person(source="person:alice", name="Alice")
BOB = Person(source="person:bob", name="Bob")
SUBJECT = "booklore_db"


def advancing_clock():
    """A wall clock one second further at each reading."""

    instants = iter(datetime(2026, 10, 3, 21, 0, 0, tzinfo=UTC) + timedelta(seconds=i) for i in range(1000))
    return lambda: next(instants)


@pytest.fixture(autouse=True)
def wall_clock(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("aistack.generators.history.wall_clock", advancing_clock())


def test_an_act_in_the_same_second_as_the_last_version_waits_for_the_next(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Two history files in one second read back as one version."""

    noon = datetime(2026, 10, 3, 12, 0, 0, 500_000, tzinfo=UTC)
    readings = iter([noon, noon, noon, noon + timedelta(seconds=1), noon + timedelta(seconds=1)])
    monkeypatch.setattr("aistack.generators.history.wall_clock", lambda: next(readings))
    slept: list[float] = []
    monkeypatch.setattr("aistack.explications.human.time.sleep", slept.append)

    write(SUBJECT, "First.", ALICE, tmp_path, expected=0)
    write(SUBJECT, "Second.", ALICE, tmp_path, expected=1)

    assert slept == [0.5]
    assert [v.artifact.content for v in versions(SUBJECT, tmp_path)] == ["First.", "Second."]


def _import(out: Path) -> None:
    now = datetime(2026, 10, 1, 10, 0, 0, tzinfo=UTC)
    record_explication(
        KnowledgeArtifact(
            id=SUBJECT,
            title=f"Explication : {SUBJECT}",
            declared_type="Explication",
            domain=UNDECLARED,
            semantic_type=UNDECLARED,
            criticality=UNDECLARED,
            owner=UNDECLARED,
            source="model:mistral",
            created_at=now,
            updated_at=now,
            confidence="Proposed",
            status=UNDECLARED,
            content="It runs hot because of its nightly scan.",
            metadata={"source_stream": "ai-reasoning", "source_instant": "2026-10-01T10-00-00Z", "explication_status": PROPOSED},
        ),
        output_dir=out,
    )


def test_writing_a_first_explication_is_a_declared_version_awaiting_validation(tmp_path: Path):
    write(SUBJECT, "Because the scan runs at night.", ALICE, tmp_path, expected=0)

    (only,) = versions(SUBJECT, tmp_path)
    assert only.artifact.content == "Because the scan runs at night."
    assert only.artifact.confidence == DECLARED
    assert only.artifact.source == "person:alice"
    assert only.artifact.metadata["explication_status"] == PROPOSED
    assert only.artifact.metadata["author_name"] == "Alice"
    assert "revision_of" not in only.artifact.metadata


def test_a_correction_revises_the_version_it_was_drawn_from(tmp_path: Path):
    _import(tmp_path)
    write(SUBJECT, "Corrected.", ALICE, tmp_path, expected=1)

    first, second = versions(SUBJECT, tmp_path)
    assert second.artifact.metadata["revision_of"] == first.instant
    assert first.artifact.content.startswith("It runs hot")  # never edited


def test_an_import_is_validated_by_any_administrator_as_a_second_author(tmp_path: Path):
    _import(tmp_path)
    validate(SUBJECT, ALICE, tmp_path, expected=1)

    first, second = versions(SUBJECT, tmp_path)
    assert second.artifact.content == first.artifact.content
    assert second.artifact.source == "model:mistral"
    assert second.artifact.confidence == "Proposed"
    assert second.artifact.metadata["explication_status"] == VALIDATED
    assert second.artifact.metadata["validated_by"] == "person:alice"
    assert second.artifact.metadata["revision_of"] == first.instant
    # The importer's own key stays with the version it wrote.
    assert "source_instant" not in second.artifact.metadata


def test_nobody_validates_their_own_text(tmp_path: Path):
    write(SUBJECT, "Mine.", ALICE, tmp_path, expected=0)

    with pytest.raises(ExplicationRefused) as refused:
        validate(SUBJECT, ALICE, tmp_path, expected=1)
    assert refused.value.reason.endswith("own_text")

    validate(SUBJECT, BOB, tmp_path, expected=1)
    assert versions(SUBJECT, tmp_path)[-1].artifact.metadata["explication_status"] == VALIDATED


def test_a_validated_version_is_not_validated_twice(tmp_path: Path):
    _import(tmp_path)
    validate(SUBJECT, ALICE, tmp_path, expected=1)

    with pytest.raises(ExplicationRefused) as refused:
        validate(SUBJECT, BOB, tmp_path, expected=2)
    assert refused.value.reason.endswith("already_validated")


def test_discarding_needs_a_reason_and_keeps_the_text(tmp_path: Path):
    _import(tmp_path)

    with pytest.raises(ExplicationRefused) as refused:
        discard(SUBJECT, "   ", ALICE, tmp_path, expected=1)
    assert refused.value.reason.endswith("no_reason")

    discard(SUBJECT, "The scan was moved to the morning.", ALICE, tmp_path, expected=1)
    first, second = versions(SUBJECT, tmp_path)
    assert second.artifact.content == first.artifact.content
    assert second.artifact.metadata["explication_status"] == DISCARDED
    assert second.artifact.metadata["discard_reason"] == "The scan was moved to the morning."
    assert second.artifact.metadata["discarded_by"] == "person:alice"

    with pytest.raises(ExplicationRefused):
        validate(SUBJECT, BOB, tmp_path, expected=2)
    with pytest.raises(ExplicationRefused):
        discard(SUBJECT, "again", BOB, tmp_path, expected=2)


def test_writing_after_a_discard_starts_a_new_proposed_version(tmp_path: Path):
    _import(tmp_path)
    discard(SUBJECT, "Wrong.", ALICE, tmp_path, expected=1)
    write(SUBJECT, "Right.", ALICE, tmp_path, expected=2)

    assert versions(SUBJECT, tmp_path)[-1].artifact.metadata["explication_status"] == PROPOSED


def test_an_act_on_a_history_that_moved_is_refused(tmp_path: Path):
    _import(tmp_path)
    write(SUBJECT, "First correction.", ALICE, tmp_path, expected=1)

    for act in (
        lambda: write(SUBJECT, "Second.", BOB, tmp_path, expected=1),
        lambda: validate(SUBJECT, BOB, tmp_path, expected=1),
        lambda: discard(SUBJECT, "Why.", BOB, tmp_path, expected=1),
    ):
        with pytest.raises(ExplicationChanged):
            act()
    assert len(versions(SUBJECT, tmp_path)) == 2


@pytest.mark.parametrize("text", ["", "   ", "x" * 20_001])
def test_an_empty_or_oversized_text_is_refused(tmp_path: Path, text: str):
    with pytest.raises(ExplicationRefused):
        write(SUBJECT, text, ALICE, tmp_path, expected=0)
    assert versions(SUBJECT, tmp_path) == []


def test_validating_or_discarding_nothing_is_refused(tmp_path: Path):
    with pytest.raises(ExplicationRefused):
        validate(SUBJECT, ALICE, tmp_path, expected=0)
    with pytest.raises(ExplicationRefused):
        discard(SUBJECT, "why", ALICE, tmp_path, expected=0)


def test_recording_the_current_text_again_is_refused(tmp_path: Path):
    """Measured on GIGABYTE, 2026-10-03: two identical versions in a row."""

    write(SUBJECT, "Same.", ALICE, tmp_path, expected=0)

    with pytest.raises(ExplicationRefused) as refused:
        write(SUBJECT, "Same.", ALICE, tmp_path, expected=1)
    assert refused.value.reason.endswith("unchanged")

    # Once discarded, the same text may be written again: it is a new claim.
    discard(SUBJECT, "Premature.", BOB, tmp_path, expected=1)
    write(SUBJECT, "Same.", ALICE, tmp_path, expected=2)
    assert len(versions(SUBJECT, tmp_path)) == 3
