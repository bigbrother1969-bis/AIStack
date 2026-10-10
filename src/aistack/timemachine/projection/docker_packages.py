"""
Project package-inventory snapshots into the graph.

One subdirectory per subject under `generated_dir / "docker-packages"`
(written by `aistack.providers.docker.packages_history`). Each subject
root is found by its `history/docker-packages` leaf, however deep the
subject's `/` nests it, and the subject string is rebuilt as the
inverse of `packages_history._output_path`.

Only `aistack:packageCount` and `aistack:packageMechanism` become graph
facts; the full package list, possibly thousands of entries, stays in
the recorded snapshot. No `aistack:occurredAt`: a snapshot says what is
installed now, not when.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history import format_instant, latest_observations
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import docker_packages_iri, stream_iri
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import (
    AISTACK_PACKAGE_COUNT,
    AISTACK_PACKAGE_MECHANISM,
    AISTACK_STABLE_SUBJECT,
    PROV_ACTIVITY,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
    XSD_DATE_TIME,
    XSD_INTEGER,
)

# Leaf names of `aistack.providers.docker.packages_history`, redeclared
# rather than imported across the writer/reader boundary.
PACKAGES_DIRNAME = "docker-packages"
STEM = "docker-packages"
STREAM_STEM = "docker-packages"


@dataclass(frozen=True)
class DockerPackagesProjectionSummary:
    """What one `project_docker_packages` run did."""

    subjects_seen: int
    snapshots_seen: int
    facts_written: int
    facts_dropped: int


def _subject_roots(packages_root: Path) -> list[tuple[str, Path]]:
    """`(subject, subject_root)` for every subject with a recorded snapshot."""

    roots: list[tuple[str, Path]] = []

    for history_leaf in sorted(packages_root.rglob(f"history/{STEM}")):
        if not history_leaf.is_dir():
            continue

        subject_root = history_leaf.parent.parent
        subject = subject_root.relative_to(packages_root).as_posix()
        roots.append((subject, subject_root))

    return roots


def project_docker_packages(
    store: GraphStore,
    generated_dir: Path = Path("reports/generated"),
    user_data_roots: Iterable[str] = (),
) -> DockerPackagesProjectionSummary:
    """
    Add every recorded package-inventory snapshot under
    `generated_dir / "docker-packages"` to `store`.

    The stream's `prov:Activity` is emitted once, only when a snapshot
    is found. Per snapshot: a `prov:Entity` with `prov:generatedAtTime`
    (recording time), `aistack:stableSubject`, `aistack:packageCount`
    and `aistack:packageMechanism`. Every fact goes through
    `filter_fact`.
    """

    packages_root = generated_dir / PACKAGES_DIRNAME
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

    if not packages_root.is_dir():
        return DockerPackagesProjectionSummary(0, 0, 0, 0)

    for subject_name, subject_root in _subject_roots(packages_root):
        subjects_seen += 1

        for observation in latest_observations(subject_root, STEM):
            instant = observation.observed_at

            parsed = json.loads(observation.read())
            if not isinstance(parsed, dict):
                continue
            mechanism = parsed.get("mechanism")
            packages = parsed.get("packages")
            if not isinstance(mechanism, str) or not isinstance(packages, list):
                continue

            if not activity_emitted:
                emit(activity, RDF_TYPE, PROV_ACTIVITY)
                activity_emitted = True

            snapshots_seen += 1
            instant_label = format_instant(instant)
            entity = docker_packages_iri(subject_name, instant_label)

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
                AISTACK_PACKAGE_COUNT,
                Literal(str(len(packages)), datatype=XSD_INTEGER),
            )
            emit(entity, AISTACK_PACKAGE_MECHANISM, Literal(mechanism))

    return DockerPackagesProjectionSummary(
        subjects_seen=subjects_seen,
        snapshots_seen=snapshots_seen,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )
