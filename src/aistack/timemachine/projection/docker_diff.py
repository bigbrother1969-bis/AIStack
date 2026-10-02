"""
Project `docker diff` snapshots into the graph — 1.5's second
collector (`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` § 1.5), cadrage
2026-09-28.

**One subdirectory per subject, not one shared batch file —
`aistack.providers.docker.diff_history` explains why on the writer
side.** This walk is the read side of the same contract: it finds
every subject root under `generated_dir / "docker-diff"` by locating
each `history/docker-diff` leaf `write_artifact_with_history` created
under it, however deep — a subject whose own name embeds a `/` (a
Compose `project/service` pair) nests one directory deeper, so this
cannot assume one `iterdir()` level per subject the way
`aistack.timemachine.projection.collection_gaps` safely can (that
module's own stream names never carry a `/`). The subject string is
rebuilt from the path between `generated_dir / "docker-diff"` and the
`history/docker-diff` leaf itself — the exact inverse of
`aistack.providers.docker.diff_history._output_path`.

**`aistack:changeCount`, not every changed path, as a graph fact.**
A `docker diff` snapshot can hold anywhere from zero to hundreds of
paths; promoting each one to its own graph triple would turn a
provenance graph meant to answer "when did this happen, for which
subject" into a bulk file-change log nothing here queries that way.
The full path list stays exactly where it was recorded — reachable
through `aistack.cli.history_query` the same way any other stream's
raw content already is — and `aistack:changeCount` gives the graph
the one lightweight magnitude signal worth a fact of its own.

**No `aistack:occurredAt`.** `docker diff` states only that a path
changed *since the container's own creation*, never when — there is
no independent instant here to state, the same restraint `ADR-0011`
§ 4 already asks of every stream that cannot state one
independently of recording time (`aistack.providers.docker.events
.occurred_at_of`'s own docstring is the one stream in this package
that can; this is not it).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history import format_instant, latest_observations
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import docker_diff_iri, stream_iri
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import (
    AISTACK_CHANGE_COUNT,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
    XSD_DATE_TIME,
    XSD_INTEGER,
)

# `aistack.providers.docker.diff_history`'s own leaf names, redeclared
# here the same way `aistack.timemachine.projection.docker_events
# .STEM` already redeclares `"docker-events"` rather than importing
# across the collector/projector boundary this package's own modules
# each keep.
DIFF_DIRNAME = "docker-diff"
STEM = "docker-diff"
STREAM_STEM = "docker-diff"


@dataclass(frozen=True)
class DockerDiffProjectionSummary:
    """What one `project_docker_diff` run actually did — the same
    measured-report shape every other stream's projection already
    gives a caller."""

    subjects_seen: int
    snapshots_seen: int
    facts_written: int
    facts_dropped: int


def _subject_roots(diff_root: Path) -> list[tuple[str, Path]]:
    """
    `(subject, subject_root)` for every subject `diff_root` actually
    holds a recorded snapshot for — found by locating each
    `history/docker-diff` leaf anywhere under `diff_root`, however
    deep a subject's own `/` nests it, rather than assuming a fixed
    depth. `subject_root.relative_to(diff_root).as_posix()` rebuilds
    the exact subject string `aistack.providers.docker.diff_history
    ._output_path` derived that nesting from in the first place.
    """

    roots: list[tuple[str, Path]] = []

    for history_leaf in sorted(diff_root.rglob(f"history/{STEM}")):
        if not history_leaf.is_dir():
            continue

        subject_root = history_leaf.parent.parent
        subject = subject_root.relative_to(diff_root).as_posix()
        roots.append((subject, subject_root))

    return roots


def project_docker_diff(
    store: GraphStore,
    generated_dir: Path = Path("reports/generated"),
    user_data_roots: Iterable[str] = (),
) -> DockerDiffProjectionSummary:
    """
    Add every recorded `docker diff` snapshot under
    `generated_dir / "docker-diff"` to `store`.

    One shared `prov:Activity` (`stream_iri("docker-diff")`) is the
    collection activity every snapshot is `prov:wasGeneratedBy` —
    emitted once, lazily, the first time this stream is actually
    found to hold a snapshot, the same guard `project_docker_events`
    already holds for the same reason (this stream lives off its own
    dedicated root, never discovered by the generic
    `available_stems` walk, so nothing else would otherwise write
    this Activity fact for a collector that has never run at all).

    For each snapshot: it exists (`prov:Entity`), when it was
    recorded (`prov:generatedAtTime` — recording time; see this
    module's own docstring for why no `aistack:occurredAt`), which
    subject it concerns (`aistack:stableSubject`, already computed by
    the collector — `ADR-0011` § 3's identity rule, "already present
    in the data, not derived here"), and how many paths it reported
    (`aistack:changeCount`).

    Every candidate fact passes through the same `filter_fact` every
    other stream's projection already uses.
    """

    diff_root = generated_dir / DIFF_DIRNAME
    activity = stream_iri(STREAM_STEM)

    subjects_seen = 0
    snapshots_seen = 0
    facts_written = 0
    facts_dropped = 0
    activity_emitted = False

    def emit(subject: str, predicate: str, obj: str | Literal) -> None:
        nonlocal facts_written, facts_dropped
        if filter_fact(subject, obj, user_data_roots):
            store.add(subject, predicate, obj)
            facts_written += 1
        else:
            facts_dropped += 1

    if not diff_root.is_dir():
        return DockerDiffProjectionSummary(0, 0, 0, 0)

    for subject_name, subject_root in _subject_roots(diff_root):
        subjects_seen += 1

        for observation in latest_observations(subject_root, STEM):
            instant = observation.observed_at

            parsed = json.loads(observation.read())
            if not isinstance(parsed, dict):
                continue
            changes = parsed.get("changes")
            if not isinstance(changes, list):
                continue

            if not activity_emitted:
                emit(activity, RDF_TYPE, PROV_ACTIVITY)
                activity_emitted = True

            snapshots_seen += 1
            instant_label = format_instant(instant)
            entity = docker_diff_iri(subject_name, instant_label)

            emit(entity, RDF_TYPE, PROV_ENTITY)
            emit(entity, PROV_WAS_GENERATED_BY, activity)
            emit(
                entity,
                PROV_GENERATED_AT_TIME,
                Literal(instant.isoformat(), datatype=XSD_DATE_TIME),
            )
            emit(entity, AISTACK_STABLE_SUBJECT, Literal(subject_name))
            emit(
                entity,
                AISTACK_CHANGE_COUNT,
                Literal(str(len(changes)), datatype=XSD_INTEGER),
            )

    return DockerDiffProjectionSummary(
        subjects_seen=subjects_seen,
        snapshots_seen=snapshots_seen,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )
