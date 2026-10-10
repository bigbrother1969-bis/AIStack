"""
Project image-digest observations into the graph.

One subdirectory per subject under `generated_dir / "docker-digest"`
(written by `aistack.providers.docker.digest_history`). Each subject
root is found by its `history/docker-digest` leaf, however deep the
subject's `/` nests it, and the subject string is rebuilt as the
inverse of `digest_history._output_path`.

Each observation states one fact, `aistack:imageDigest`. No
`aistack:occurredAt`: an observation says what the digest is now, not
when it changed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history import format_instant, latest_observations
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import docker_digest_iri, stream_iri
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import (
    AISTACK_IMAGE_DIGEST,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
    XSD_DATE_TIME,
)

# Leaf names of `aistack.providers.docker.digest_history`, redeclared
# rather than imported across the writer/reader boundary.
DIGEST_DIRNAME = "docker-digest"
STEM = "docker-digest"
STREAM_STEM = "docker-digest"


@dataclass(frozen=True)
class DockerDigestProjectionSummary:
    """What one `project_docker_digest` run did."""

    subjects_seen: int
    snapshots_seen: int
    facts_written: int
    facts_dropped: int


def _subject_roots(digest_root: Path) -> list[tuple[str, Path]]:
    """`(subject, subject_root)` for every subject with a recorded observation."""

    roots: list[tuple[str, Path]] = []

    for history_leaf in sorted(digest_root.rglob(f"history/{STEM}")):
        if not history_leaf.is_dir():
            continue

        subject_root = history_leaf.parent.parent
        subject = subject_root.relative_to(digest_root).as_posix()
        roots.append((subject, subject_root))

    return roots


def project_docker_digest(
    store: GraphStore,
    generated_dir: Path = Path("reports/generated"),
    user_data_roots: Iterable[str] = (),
) -> DockerDigestProjectionSummary:
    """
    Add every recorded image-digest observation under
    `generated_dir / "docker-digest"` to `store`.

    The stream's `prov:Activity` is emitted once, only when an
    observation is found. Per observation: a `prov:Entity` with
    `prov:generatedAtTime` (recording time), `aistack:stableSubject`
    and `aistack:imageDigest`. Every fact goes through `filter_fact`.
    """

    digest_root = generated_dir / DIGEST_DIRNAME
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

    if not digest_root.is_dir():
        return DockerDigestProjectionSummary(0, 0, 0, 0)

    for subject_name, subject_root in _subject_roots(digest_root):
        subjects_seen += 1

        for observation in latest_observations(subject_root, STEM):
            instant = observation.observed_at

            parsed = json.loads(observation.read())
            if not isinstance(parsed, dict):
                continue
            digest = parsed.get("digest")
            if not isinstance(digest, str):
                continue

            if not activity_emitted:
                emit(activity, RDF_TYPE, PROV_ACTIVITY)
                activity_emitted = True

            snapshots_seen += 1
            instant_label = format_instant(instant)
            entity = docker_digest_iri(subject_name, instant_label)

            emit(entity, RDF_TYPE, PROV_ENTITY)
            emit(entity, PROV_WAS_GENERATED_BY, activity)
            emit(
                entity,
                PROV_GENERATED_AT_TIME,
                Literal(instant.isoformat(), datatype=XSD_DATE_TIME),
            )
            emit(entity, AISTACK_STABLE_SUBJECT, Literal(subject_name))
            emit(entity, AISTACK_IMAGE_DIGEST, Literal(digest))

    return DockerDigestProjectionSummary(
        subjects_seen=subjects_seen,
        snapshots_seen=snapshots_seen,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )
