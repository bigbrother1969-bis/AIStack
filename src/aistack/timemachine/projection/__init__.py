from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history import available_instants, available_stems, format_instant, observation_at
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import (
    agent_iri as _agent_iri,
    observation_iri as _entity_iri,
    request_iri as _request_iri,
    stream_iri as _activity_iri,
)
from aistack.timemachine.projection.docker_events import (
    DockerEventsProjectionSummary,
    project_docker_events,
)
from aistack.timemachine.projection.explications import (
    ExplicationProjectionSummary,
    project_explications,
)
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import (
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_AGENT,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_USED,
    PROV_WAS_ATTRIBUTED_TO,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
    XSD_DATE_TIME,
)

# STD-0002's own reasoning, extended here: a project-relative
# default, matching every CLI module that already redeclares
# `GENERATED_DIR = Path("reports/generated")`
# (`aistack.cli.history_query`, `aistack.cli.health_render`) rather
# than importing a shared constant nothing in this heritage has ever
# declared.
DEFAULT_GENERATED_DIR = Path("reports/generated")

# `RDF_TYPE`/`XSD_DATE_TIME` and the four IRI builders used to live
# here, inline — moved to `aistack.timemachine.vocabulary` and
# `aistack.timemachine.iri` 2026-09-27 so `timemachine_ui` (the first
# reader of this graph other than its own tests) can share the exact
# same constants and construction rather than re-deriving them. The
# aliases above keep every call below unchanged; this module remains
# the one writer.


def _parse_envelope(content: str) -> tuple[str, str, str | None] | None:
    """
    `(stable_subject, origin, causality)` read from `content` when it
    carries the `version`/`provenance` envelope J3 gave three of the
    four historicised streams (`decision_history.serialize_decision`,
    `reasoning_history.serialize_ai_reasoning`,
    `tracing.serialization.serialize_execution_trace` — each
    documented as writing exactly `{"version": {"subject", ...},
    "provenance": {"origin", "causality"}, ...}`). `None` for
    anything else: the raw Observation History streams (the twelve
    provider generators) carry no such envelope, and at least one
    artifact (`DockerExplanationArtifactGenerator`'s own sentences)
    is not even JSON.

    Checked structurally — the two keys and their inner shape — not
    by stem name or module origin, so a stream that gains this
    envelope later is picked up without this module changing, the
    same reasoning `aistack.conformance.inventory` already holds for
    a Protocol's structural satisfaction over nominal inheritance.
    """

    try:
        parsed = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    if not isinstance(parsed, dict):
        return None

    version = parsed.get("version")
    provenance = parsed.get("provenance")

    if not isinstance(version, dict) or not isinstance(provenance, dict):
        return None

    subject = version.get("subject")
    origin = provenance.get("origin")

    if not isinstance(subject, str) or not isinstance(origin, str):
        return None

    causality = provenance.get("causality")
    if causality is not None and not isinstance(causality, str):
        return None

    return subject, origin, causality


@dataclass(frozen=True)
class ProjectionSummary:
    """What one `project_observation_history` run actually did — a
    measured report, not a guess, for whoever triggers a rebuild."""

    streams_seen: int
    observations_seen: int
    facts_written: int
    facts_dropped: int


def project_observation_history(
    store: GraphStore,
    generated_dir: Path = DEFAULT_GENERATED_DIR,
    user_data_roots: Iterable[str] = (),
) -> ProjectionSummary:
    """
    Rebuild `store` from every stream Observation History currently
    holds under `generated_dir` — `ADR-0011` § *Decision* 1 and 10: a
    full rebuild every time, `store.clear()`'d first, never
    incremental.

    **Two tiers of fact, honest about what each stream actually
    states.** Every historical observation, of any stream, gets the
    generic baseline nothing here has to guess at: it existed
    (`prov:Entity`), when it was recorded (`prov:generatedAtTime` —
    recording time only; no `aistack:occurredAt` is invented for an
    instant already only known as "when this was written"), and which
    stream's own collection activity produced it
    (`prov:wasGeneratedBy`). Where a stream's own content parses as
    the `version`/`provenance` envelope (`_parse_envelope`), three
    more real facts are added: `aistack:stableSubject`
    (`version.subject` — R3's stable identity, already present in the
    data, not derived here), `prov:wasAttributedTo` an Agent
    (`provenance.origin`), and, when a request caused the write,
    `prov:used` naming it (`provenance.causality` — an Activity
    *using* the Entity that triggered it is exactly what this
    predicate states in PROV-O, not a new predicate invented for it).

    **Deliberately not attempted**: parsing each of the twelve raw
    Observation History streams' own business schema (a Docker
    container's identity, a Beszel host's own name, and so on) —
    real, richer facts a *collector* states, which is 1.5's concern
    (`ADR-0011` § *Open Points*: "how `aistack:occurredAt` is
    populated ... 1.5's collectors"). Guessing that mapping now, for
    streams none of the owner's collectors emit yet in that shape,
    is exactly the invented infrastructure `ARC-P-006` forbids.

    Every candidate fact passes through
    `aistack.timemachine.projection.filter.filter_fact` before
    `store.add` — the ADR's own name for this pass — so
    `user_data_roots` reaches every stream this walk visits, present
    or future, without this function's own logic changing.
    """

    store.clear()

    streams_seen = 0
    observations_seen = 0
    facts_written = 0
    facts_dropped = 0

    def emit(subject: str, predicate: str, obj: str | Literal) -> None:
        nonlocal facts_written, facts_dropped
        if filter_fact(subject, obj, user_data_roots):
            store.add(subject, predicate, obj)
            facts_written += 1
        else:
            facts_dropped += 1

    for stem in available_stems(generated_dir):
        streams_seen += 1
        activity = _activity_iri(stem)
        emit(activity, RDF_TYPE, PROV_ACTIVITY)

        for instant in available_instants(generated_dir, stem):
            observation = observation_at(generated_dir, stem, instant)
            if observation is None:
                continue

            observations_seen += 1
            entity = _entity_iri(stem, format_instant(observation.observed_at))

            emit(entity, RDF_TYPE, PROV_ENTITY)
            emit(entity, PROV_WAS_GENERATED_BY, activity)
            emit(
                entity,
                PROV_GENERATED_AT_TIME,
                Literal(
                    observation.observed_at.isoformat(), datatype=XSD_DATE_TIME
                ),
            )

            envelope = _parse_envelope(observation.read())
            if envelope is not None:
                subject, origin, causality = envelope
                emit(entity, AISTACK_STABLE_SUBJECT, Literal(subject))

                agent = _agent_iri(origin)
                emit(agent, RDF_TYPE, PROV_AGENT)
                emit(entity, PROV_WAS_ATTRIBUTED_TO, agent)

                if causality is not None:
                    request = _request_iri(causality)
                    emit(request, RDF_TYPE, PROV_ENTITY)
                    emit(activity, PROV_USED, request)

    return ProjectionSummary(
        streams_seen=streams_seen,
        observations_seen=observations_seen,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )


__all__ = [
    "DEFAULT_GENERATED_DIR",
    "DockerEventsProjectionSummary",
    "ExplicationProjectionSummary",
    "ProjectionSummary",
    "project_docker_events",
    "project_explications",
    "project_observation_history",
]
