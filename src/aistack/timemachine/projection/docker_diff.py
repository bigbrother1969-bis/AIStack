"""
Project `docker diff` snapshots into the graph.

One subdirectory per subject under `generated_dir / "docker-diff"`
(written by `aistack.providers.docker.diff_history`). A subject with a
`/` (a Compose `project/service` pair) nests deeper, so subject roots
are found by their `history/docker-diff` leaf at any depth, and the
subject string is rebuilt as the inverse of `diff_history._output_path`.

Only `aistack:changeCount` becomes a graph fact; the full path list
stays in the recorded snapshot. No `aistack:occurredAt` (`ADR-0011`
§ 4): `docker diff` says a path changed since the container was
created, not when.
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

# Leaf names of `aistack.providers.docker.diff_history`, redeclared
# rather than imported across the writer/reader boundary.
DIFF_DIRNAME = "docker-diff"
STEM = "docker-diff"
STREAM_STEM = "docker-diff"


@dataclass(frozen=True)
class DockerDiffProjectionSummary:
    """What one `project_docker_diff` run did."""

    subjects_seen: int
    snapshots_seen: int
    facts_written: int
    facts_dropped: int


def _subject_roots(diff_root: Path) -> list[tuple[str, Path]]:
    """
    `(subject, subject_root)` for every subject with a recorded
    snapshot, found by its `history/docker-diff` leaf at any depth.
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

    The stream's `prov:Activity` is emitted once, only when a snapshot
    is found. Per snapshot: a `prov:Entity` with `prov:generatedAtTime`
    (recording time), `aistack:stableSubject` and
    `aistack:changeCount`. Every fact goes through `filter_fact`.
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
