"""
Project Docker events into the graph — 1.5's first collector
(`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` § 1.5), cadrage 2026-09-28.

**A separate function, not a branch inside `project_observation_history`
— the same reason `project_explications` is one.** That function's
two-tier fact model (generic baseline + the `version`/`provenance`
envelope) is shaped for a stream whose content is one subject's own
snapshot; a Docker-events batch is a different shape entirely — a
`since`/`until` window holding zero or more discrete events, each with
its *own* subject. Forcing it through the existing envelope parser
would see no envelope and silently fall back to one generic Entity for
the whole batch — losing exactly the per-event `aistack:stableSubject`/
`aistack:occurredAt` facts this module exists to add.

**Lives off `project_observation_history`'s own root, on purpose.**
`aistack.providers.docker.events_history.DEFAULT_OUTPUT_PATH` writes
under `generated_dir / "docker-events"`, not `generated_dir` itself —
see that module's own comment. `available_stems(generated_dir)` never
finds it, so the generic walk and this one never double-project the
same batch.

**Does not clear the store.** `project_observation_history` already
does that once per rebuild (`ADR-0011` § *Decision* 10); this function
is the third source stream in the same rebuild pass
(`aistack.cli.timemachine_rebuild.main`), added after Explications.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history import available_instants, format_instant, observation_at
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import docker_event_iri, stream_iri
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import (
    AISTACK_DOCKER_ACTION,
    AISTACK_OCCURRED_AT,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
    XSD_DATE_TIME,
)

# The one stream this projector reads — `aistack.providers.docker
# .events_history.record_docker_events`' own stem, `"docker-events"`,
# under its own dedicated root. Named as a constant here rather than
# imported from that module: the writer lives in `aistack.providers`
# (a collector's own domain), this reads generically by stem the same
# way `project_explications` reads `"explications"` by directory name
# rather than importing a sibling module across that boundary.
STEM = "docker-events"


@dataclass(frozen=True)
class DockerEventsProjectionSummary:
    """What one `project_docker_events` run actually did — the same
    measured-report shape `ProjectionSummary`/`ExplicationProjectionSummary`
    already give a caller for the other streams."""

    batches_seen: int
    events_seen: int
    facts_written: int
    facts_dropped: int


def project_docker_events(
    store: GraphStore,
    generated_dir: Path = Path("reports/generated"),
    user_data_roots: Iterable[str] = (),
) -> DockerEventsProjectionSummary:
    """
    Add every recorded Docker-events batch under
    `generated_dir / "docker-events"` to `store`.

    One shared `prov:Activity` (`stream_iri("docker-events")`, the
    same construction a stem picked up by the generic walk would have
    received) is the collection activity every event in every batch is
    `prov:wasGeneratedBy`. For each event within each batch: it exists
    (`prov:Entity`), when the batch that recorded it was written
    (`prov:generatedAtTime` — recording time, the batch's own
    historicised instant, the same "recording time only" honesty every
    other stream's projection already keeps), when Docker itself says
    it happened (`aistack:occurredAt` — `ADR-0011` § 4's own
    unfulfilled field, first populated here, since this is the first
    collector able to state it independently of recording time), which
    subject it concerns (`aistack:stableSubject`, already computed by
    the collector — `ADR-0011` § 3's identity rule, "already present
    in the data, not derived here", the same restraint
    `project_observation_history`'s own docstring already names) and
    what Docker recorded as having happened (`aistack:dockerAction`).

    **`aistack:clockSource` is not written here.** `ADR-0011` § 5
    reserves that field for once a collector "runs on more than one
    host" and a drift measurement exists between their clocks; this
    first collector runs on GIGABYTE alone, so there is no second
    clock yet to measure drift against — recorded as a fact this
    module does not yet have, not invented ahead of the SSH-remote-host
    collection § 1.5 itself sequences after GIGABYTE.

    Every candidate fact passes through the same `filter_fact` every
    other stream's projection already uses, so `user_data_roots`
    reaches this stream too without this function's own logic
    changing.
    """

    docker_events_dir = generated_dir / "docker-events"
    activity = stream_iri(STEM)

    batches_seen = 0
    events_seen = 0
    facts_written = 0
    facts_dropped = 0

    def emit(subject: str, predicate: str, obj: str | Literal) -> None:
        nonlocal facts_written, facts_dropped
        if filter_fact(subject, obj, user_data_roots):
            store.add(subject, predicate, obj)
            facts_written += 1
        else:
            facts_dropped += 1

    for instant in available_instants(docker_events_dir, STEM):
        observation = observation_at(docker_events_dir, STEM, instant)
        if observation is None:
            continue

        if batches_seen == 0:
            # Emitted once, lazily, the first time this stream is
            # actually found to have data — never unconditionally: the
            # generic walk's own `emit(activity, RDF_TYPE,
            # PROV_ACTIVITY)` only runs for a stem `available_stems`
            # actually returned, and this stream is not discovered
            # that way (it lives off that walk's own root, on
            # purpose — see this module's docstring), so nothing else
            # would otherwise guard against writing an Activity fact
            # for a collector that has never run at all.
            emit(activity, RDF_TYPE, PROV_ACTIVITY)

        batches_seen += 1
        parsed = json.loads(observation.read())
        events = parsed.get("events") if isinstance(parsed, dict) else None
        if not isinstance(events, list):
            continue

        instant_label = format_instant(instant)

        for index, event in enumerate(events):
            if not isinstance(event, dict):
                continue

            events_seen += 1
            entity = docker_event_iri(instant_label, index)

            emit(entity, RDF_TYPE, PROV_ENTITY)
            emit(entity, PROV_WAS_GENERATED_BY, activity)
            emit(
                entity,
                PROV_GENERATED_AT_TIME,
                Literal(instant.isoformat(), datatype=XSD_DATE_TIME),
            )

            occurred_at = event.get("occurred_at")
            if isinstance(occurred_at, str):
                emit(
                    entity,
                    AISTACK_OCCURRED_AT,
                    Literal(occurred_at, datatype=XSD_DATE_TIME),
                )

            subject = event.get("subject")
            if isinstance(subject, str):
                emit(entity, AISTACK_STABLE_SUBJECT, Literal(subject))

            action = event.get("action")
            if isinstance(action, str) and action:
                emit(entity, AISTACK_DOCKER_ACTION, Literal(action))

    return DockerEventsProjectionSummary(
        batches_seen=batches_seen,
        events_seen=events_seen,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )
