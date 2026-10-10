"""
Project Explications into the graph (`ADR-0011` § 7-8).

Separate from `project_observation_history`: an Explication is a
`KnowledgeArtifact` document, not a collector observation with a
`version`/`provenance` envelope.

Does not clear the store: `project_observation_history` does that once
per rebuild, and this runs after it in the same pass.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history.subject_names import subject_for_stem
from aistack.explications import deserialize_explication
from aistack.history import available_stems, every_version
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import agent_iri, explication_iri, subject_iri
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import (
    AISTACK_CONFIDENCE,
    AISTACK_EXPLAINS,
    AISTACK_EXPLICATION_STATUS,
    PROV_AGENT,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_WAS_ATTRIBUTED_TO,
    PROV_WAS_REVISION_OF,
    RDF_TYPE,
    XSD_DATE_TIME,
)


@dataclass(frozen=True)
class ExplicationProjectionSummary:
    """What one `project_explications` run did."""

    subjects_seen: int
    explications_seen: int
    facts_written: int
    facts_dropped: int


def project_explications(
    store: GraphStore,
    generated_dir: Path = Path("reports/generated"),
    user_data_roots: Iterable[str] = (),
) -> ExplicationProjectionSummary:
    """
    Add every recorded version of every Explication under
    `generated_dir/explications/` to `store` (a correction is one more
    entity, `ADR-0011` § 7).

    Per version: a `prov:Entity` with `prov:generatedAtTime`
    (`created_at`), `aistack:explains` (the subject's IRI),
    `aistack:confidence`, `aistack:explicationStatus` when set, and
    `prov:wasAttributedTo` the agent named by `artifact.source`. Every
    fact goes through `filter_fact`.
    """

    explications_dir = generated_dir / "explications"

    subjects_seen = 0
    explications_seen = 0
    facts_written = 0
    facts_dropped = 0

    def emit(subject: str, predicate: str, obj: str | Literal) -> None:
        nonlocal facts_written, facts_dropped
        if filter_fact(subject, obj, user_data_roots):
            store.add(subject, predicate, obj)
            facts_written += 1
        else:
            facts_dropped += 1

    for stem in available_stems(explications_dir):
        subject = subject_for_stem(stem)
        subjects_seen += 1
        explained = subject_iri(subject)

        # Every version, including two written in the same second: each
        # has its own node, named by its file.
        for observation in every_version(explications_dir, stem):
            explications_seen += 1
            artifact = deserialize_explication(json.loads(observation.read()))
            entity = explication_iri(subject, observation.label)

            emit(entity, RDF_TYPE, PROV_ENTITY)
            emit(
                entity,
                PROV_GENERATED_AT_TIME,
                Literal(artifact.created_at.isoformat(), datatype=XSD_DATE_TIME),
            )
            emit(entity, AISTACK_EXPLAINS, explained)
            emit(entity, AISTACK_CONFIDENCE, Literal(artifact.confidence))

            status = artifact.metadata.get("explication_status")
            if status is not None:
                emit(entity, AISTACK_EXPLICATION_STATUS, Literal(str(status)))

            agent = agent_iri(artifact.source)
            emit(agent, RDF_TYPE, PROV_AGENT)
            emit(entity, PROV_WAS_ATTRIBUTED_TO, agent)

            # A person's act revises the version it was drawn from, and
            # a validation names a second, confirming author (ADR-0015
            # § 5, ADR-0011 § 7).
            revision_of = artifact.metadata.get("revision_of")
            if revision_of:
                emit(entity, PROV_WAS_REVISION_OF, explication_iri(subject, str(revision_of)))
            validated_by = artifact.metadata.get("validated_by")
            if validated_by:
                validator = agent_iri(str(validated_by))
                emit(validator, RDF_TYPE, PROV_AGENT)
                emit(entity, PROV_WAS_ATTRIBUTED_TO, validator)

    return ExplicationProjectionSummary(
        subjects_seen=subjects_seen,
        explications_seen=explications_seen,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )
