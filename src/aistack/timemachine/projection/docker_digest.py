"""
Project image-digest observations into the graph — 1.5's third
collector (`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` § 1.5), cadrage
2026-09-28.

**One subdirectory per subject, not one shared batch file — the same
reasoning `aistack.timemachine.projection.docker_diff` already gives
for its own write side (`aistack.providers.docker.digest_history`
explains it there).** This walk is the read side of the same
contract, unchanged from that module's own: it finds every subject
root under `generated_dir / "docker-digest"` by locating each
`history/docker-digest` leaf, however deep a subject's own `/` nests
it, and rebuilds the subject string the exact inverse way
`aistack.providers.docker.digest_history._output_path` derived it.

**`aistack:imageDigest`, the one fact this stream states.** Unlike
`docker diff`, which reports a whole list of changed paths a graph
fact would have to summarise (`aistack:changeCount`), an image-digest
observation is already a single value — the current digest itself is
exactly the fact worth stating, with no summarising needed.

**No `aistack:occurredAt`, the same restraint `docker_diff`'s own
module already documents for the same reason.** A digest observed
this cycle states only that this is the digest *now*, not when it
last changed — there is no independent instant here to state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history import available_instants, format_instant, observation_at
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

# `aistack.providers.docker.digest_history`'s own leaf names,
# redeclared here — the same cross-boundary convention
# `aistack.timemachine.projection.docker_diff`'s own module already
# redeclares `"docker-diff"` for.
DIGEST_DIRNAME = "docker-digest"
STEM = "docker-digest"
STREAM_STEM = "docker-digest"


@dataclass(frozen=True)
class DockerDigestProjectionSummary:
    """What one `project_docker_digest` run actually did — the same
    measured-report shape every other stream's projection already
    gives a caller."""

    subjects_seen: int
    snapshots_seen: int
    facts_written: int
    facts_dropped: int


def _subject_roots(digest_root: Path) -> list[tuple[str, Path]]:
    """
    `(subject, subject_root)` for every subject `digest_root` actually
    holds a recorded observation for — the same `rglob`-based walk
    `aistack.timemachine.projection.docker_diff._subject_roots`
    already holds, unchanged in shape, against this stream's own leaf
    name.
    """

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

    One shared `prov:Activity` (`stream_iri("docker-digest")`) is the
    collection activity every observation is `prov:wasGeneratedBy` —
    emitted once, lazily, the first time this stream is actually found
    to hold an observation, the same guard `project_docker_diff`
    already holds for the same reason (this stream lives off its own
    dedicated root, never discovered by the generic `available_stems`
    walk).

    For each observation: it exists (`prov:Entity`), when it was
    recorded (`prov:generatedAtTime` — recording time; see this
    module's own docstring for why no `aistack:occurredAt`), which
    subject it concerns (`aistack:stableSubject`), and its own current
    image digest (`aistack:imageDigest`).

    Every candidate fact passes through the same `filter_fact` every
    other stream's projection already uses.
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

        for instant in available_instants(subject_root, STEM):
            observation = observation_at(subject_root, STEM, instant)
            if observation is None:
                continue

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
