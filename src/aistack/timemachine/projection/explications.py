"""
Project Explications into the graph — `ADR-0011` § *Decision* 7-8,
the fifth source stream `project_observation_history`'s own docstring
already promised ("soon five").

**A separate function, not a branch inside `project_observation_history`
— on purpose.** That function's two-tier fact model (generic baseline
+ the `version`/`provenance` envelope) is shaped for a *collector*
observing a live system repeatedly; an Explication is a *document*
about something, with its own distinct shape
(`aistack.contracts.artifact.KnowledgeArtifact`, no `version`/
`provenance` pair at all — see that module's own comment on why).
Forcing Explications through the existing envelope parser would
either silently produce nothing (the shapes do not match) or require
bending that parser to recognise a second envelope shape it was never
about — the same "fifth mechanism where a fourth one does not
actually fit" the AI Reasoning History's own patch notes warned
against for a different case.

**Does not clear the store.** `project_observation_history` already
does that once per rebuild (`ADR-0011` § *Decision* 10); this function
is the second half of the same rebuild pass, called after it
(`aistack.cli.timemachine_rebuild.main`), adding Explications' own
facts on top rather than starting a second, independent graph.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.explications import deserialize_explication
from aistack.history import available_stems, format_instant, latest_observations
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
    RDF_TYPE,
    XSD_DATE_TIME,
)


@dataclass(frozen=True)
class ExplicationProjectionSummary:
    """What one `project_explications` run actually did — the same
    measured-report shape `ProjectionSummary` already gives a caller
    for the four existing streams."""

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
    Add every recorded Explication under
    `generated_dir/explications/` to `store` — every subject that has
    ever had one, every version ever recorded for it (`ADR-0011` § 7:
    "nothing already written is edited or removed", so a correction is
    one more Explication entity, not a replacement of the last).

    For each Explication: it exists (`prov:Entity`), when it was
    recorded (`prov:generatedAtTime`, `artifact.created_at` — the
    Explication's own recording time, the same "recording time only"
    honesty `project_observation_history` already keeps), what it
    explains (`aistack:explains`, `subject_iri` — a bare reference, not
    a claim about what kind of thing the subject is), its `STD-0100`
    confidence (`aistack:confidence`) and, when recorded, its workflow
    position (`aistack:explicationStatus`, from
    `artifact.metadata["explication_status"]` — absent rather than
    guessed when an importer has not set it), and who or what produced
    it (`prov:wasAttributedTo` an Agent named by `artifact.source`,
    the same `agent_iri` construction the four existing streams'
    `provenance.origin` already uses).

    Every candidate fact passes through the same `filter_fact` the
    four existing streams already do, so `user_data_roots` reaches
    Explications too without this function's own logic changing.
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

    for subject in available_stems(explications_dir):
        subjects_seen += 1
        explained = subject_iri(subject)

        for observation in latest_observations(explications_dir, subject):
            instant = observation.observed_at

            explications_seen += 1
            artifact = deserialize_explication(json.loads(observation.read()))
            entity = explication_iri(subject, format_instant(instant))

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

    return ExplicationProjectionSummary(
        subjects_seen=subjects_seen,
        explications_seen=explications_seen,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )
