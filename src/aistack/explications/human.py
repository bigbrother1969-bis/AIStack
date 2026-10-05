"""
A person writes, validates or discards an Explication (`ADR-0015`).

Each act is one more version in the subject's history — nothing already
written is edited or removed (`ADR-0011` § 7). The three acts check the
history they were drawn from (`expected`, the number of versions the
form saw) so two administrators never stack a version on one they have
not read (`ADR-0015` § 6).

In the development phase (`ADR-0016`), an administrator's text is
validated as written, an author may validate their own text, and a
subject's whole history can be purged — the one exception to "nothing
is ever deleted", for test entries made while AIStack is set up.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from aistack.generators import history as history_files

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.explications.store import deserialize_explication, record_explication
from aistack.history import every_version, format_instant
from aistack.history.subject_names import stem_for_subject

PROPOSED = "Proposed"
VALIDATED = "Validated"
DISCARDED = "Discarded"
DECLARED = "Declared"

PERSON_PREFIX = "person:"
MAX_TEXT = 20_000
MAX_REASON = 1_000
MAX_SUBJECT = 200


@dataclass(frozen=True)
class Person:
    """Who acts: `source` is what the graph attributes to, `name` what
    the page shows."""

    source: str
    name: str


@dataclass(frozen=True)
class Version:
    """One recorded version and the instant label its graph node is
    keyed by (`aistack.timemachine.iri.explication_iri`)."""

    instant: str
    artifact: KnowledgeArtifact


class ExplicationRefused(Exception):
    """An act the rules of `ADR-0015` refuse; `reason` is an i18n key."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class ExplicationChanged(ExplicationRefused):
    """The history moved since the form was drawn (`ADR-0015` § 6)."""

    def __init__(self) -> None:
        super().__init__("timemachine.explication.refused.changed")


def person_source(subject: str) -> str:
    return PERSON_PREFIX + subject


def versions(subject: str, output_dir: Path) -> list[Version]:
    """Every version of `subject`'s Explication, oldest first, each with
    its instant."""

    return [
        Version(
            instant=observation.label,
            artifact=deserialize_explication(json.loads(observation.read())),
        )
        for observation in every_version(output_dir, stem_for_subject(subject))
    ]


def status_of(artifact: KnowledgeArtifact) -> str:
    return str(artifact.metadata.get("explication_status", PROPOSED))


def author_of(artifact: KnowledgeArtifact) -> str:
    """The source of the text — the author, never the validator."""

    return artifact.source


def _a_second_of_its_own(history: list[Version]) -> datetime:
    """
    The instant the new version is recorded at, strictly after the last
    one's second. Since 1.9 two versions written in one second both read
    back (`aistack.history.every_version`); an act still takes a second
    of its own, so its recorded time is never the same as the version it
    acts on. A person's acts are seconds apart; when one is not, it waits.
    """

    while True:
        now = history_files.wall_clock()
        if not history or format_instant(now) > history[-1].instant:
            return now
        time.sleep(1 - now.microsecond / 1_000_000)


def _checked_subject(subject: str) -> str:
    subject = subject.strip()
    if not subject or len(subject) > MAX_SUBJECT:
        raise ExplicationRefused("timemachine.explication.refused.subject")
    return subject


def _current(subject: str, output_dir: Path, expected: int) -> list[Version]:
    history = versions(subject, output_dir)
    if len(history) != expected:
        raise ExplicationChanged()
    return history


def _record(
    previous: Version | None,
    subject: str,
    *,
    content: str,
    source: str,
    confidence: str,
    metadata: dict[str, object],
    output_dir: Path,
    now: datetime,
) -> None:
    if previous is not None:
        metadata = {**metadata, "revision_of": previous.instant}
    record_explication(
        KnowledgeArtifact(
            id=subject,
            title=f"Explication : {subject}",
            declared_type="Explication",
            domain=UNDECLARED,
            semantic_type=UNDECLARED,
            criticality=UNDECLARED,
            owner=UNDECLARED,
            source=source,
            created_at=now,
            updated_at=now,
            confidence=confidence,
            status=UNDECLARED,
            content=content,
            metadata=metadata,
        ),
        output_dir=output_dir,
    )


def write(
    subject: str,
    text: str,
    person: Person,
    output_dir: Path,
    expected: int,
    development: bool = False,
) -> None:
    """A new `Declared` version written by `person` (`ADR-0015` § 2) —
    in the development phase, validated by its author as written
    (`ADR-0016`)."""

    subject = _checked_subject(subject)
    if not text.strip():
        raise ExplicationRefused("timemachine.explication.refused.empty")
    if len(text) > MAX_TEXT:
        raise ExplicationRefused("timemachine.explication.refused.too_long")

    history = _current(subject, output_dir, expected)
    if history and status_of(history[-1].artifact) != DISCARDED and history[-1].artifact.content == text:
        # Recording the same text again says nothing new (measured on
        # GIGABYTE, 2026-10-03: two identical versions in a row).
        raise ExplicationRefused("timemachine.explication.refused.unchanged")
    _record(
        history[-1] if history else None,
        subject,
        content=text,
        source=person.source,
        confidence=DECLARED,
        metadata={
            "source_stream": "person",
            "author_name": person.name,
            "explication_status": PROPOSED,
        }
        if not development
        else {
            "source_stream": "person",
            "author_name": person.name,
            "explication_status": VALIDATED,
            "validated_by": person.source,
            "validated_by_name": person.name,
            "validated_in": "development",
        },
        output_dir=output_dir,
        now=_a_second_of_its_own(history),
    )


def validate(
    subject: str,
    person: Person,
    output_dir: Path,
    expected: int,
    development: bool = False,
) -> None:
    """`person` confirms the current version, written by someone else
    (`ADR-0015` § 3) — or by themselves, in the development phase
    (`ADR-0016`)."""

    subject = _checked_subject(subject)
    history = _current(subject, output_dir, expected)
    if not history:
        raise ExplicationRefused("timemachine.explication.refused.nothing")

    current = history[-1]
    status = status_of(current.artifact)
    if status in (VALIDATED, DISCARDED):
        raise ExplicationRefused(f"timemachine.explication.refused.already_{status.lower()}")
    if author_of(current.artifact) == person.source and not development:
        raise ExplicationRefused("timemachine.explication.refused.own_text")

    _record(
        current,
        subject,
        content=current.artifact.content,
        source=current.artifact.source,
        confidence=current.artifact.confidence,
        metadata={
            **_kept(current.artifact),
            "explication_status": VALIDATED,
            "validated_by": person.source,
            "validated_by_name": person.name,
            **({"validated_in": "development"} if development else {}),
        },
        output_dir=output_dir,
        now=_a_second_of_its_own(history),
    )


def validate_declared(person: Person, output_dir: Path) -> list[str]:
    """
    Validate every subject whose current version is a person's text
    still waiting (`Declared`, `Proposed`) — the owner's decision of
    2026-10-04 for the development phase (`ADR-0016`). Returns the
    subjects validated. Imported versions (`Proposed` confidence) are
    left to be read one by one.
    """

    from aistack.history import available_stems
    from aistack.history.subject_names import subject_for_stem

    validated = []
    for stem in available_stems(output_dir):
        subject = subject_for_stem(stem)
        history = versions(subject, output_dir)
        if not history:
            continue
        current = history[-1].artifact
        if current.confidence == DECLARED and status_of(current) == PROPOSED:
            validate(subject, person, output_dir, expected=len(history), development=True)
            validated.append(subject)
    return validated


def purge(subject: str, output_dir: Path) -> int:
    """
    Delete every version of `subject`'s Explication — the development
    phase's one exception to "nothing is ever deleted" (`ADR-0016`),
    for entries made while testing. Returns the number of versions
    removed; the graph forgets them at its next rebuild.
    """

    subject = _checked_subject(subject)
    stem = stem_for_subject(subject)
    count = len(versions(subject, output_dir))
    (output_dir / f"{stem}.json").unlink(missing_ok=True)
    history_dir = output_dir / "history" / stem
    if history_dir.is_dir():
        shutil.rmtree(history_dir)
    return count


def discard(
    subject: str,
    reason: str,
    person: Person,
    output_dir: Path,
    expected: int,
) -> None:
    """The current version set aside, with `person`'s reason
    (`ADR-0015` § 4)."""

    subject = _checked_subject(subject)
    reason = reason.strip()
    if not reason:
        raise ExplicationRefused("timemachine.explication.refused.no_reason")
    if len(reason) > MAX_REASON:
        raise ExplicationRefused("timemachine.explication.refused.too_long")

    history = _current(subject, output_dir, expected)
    if not history:
        raise ExplicationRefused("timemachine.explication.refused.nothing")

    current = history[-1]
    if status_of(current.artifact) == DISCARDED:
        raise ExplicationRefused("timemachine.explication.refused.already_discarded")

    _record(
        current,
        subject,
        content=current.artifact.content,
        source=current.artifact.source,
        confidence=current.artifact.confidence,
        metadata={
            **_kept(current.artifact),
            "explication_status": DISCARDED,
            "discarded_by": person.source,
            "discarded_by_name": person.name,
            "discard_reason": reason,
        },
        output_dir=output_dir,
        now=_a_second_of_its_own(history),
    )


# What a validation or a discard carries over from the version it acts
# on: where the text came from and who wrote it — never a previous
# act's own marks, nor an importer's de-duplication key, which belongs
# to the version the importer wrote.
_CARRIED = ("source_stream", "author_name")


def _kept(artifact: KnowledgeArtifact) -> dict[str, object]:
    return {key: artifact.metadata[key] for key in _CARRIED if key in artifact.metadata}
