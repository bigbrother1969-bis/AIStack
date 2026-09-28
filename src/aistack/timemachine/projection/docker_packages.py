"""
Project package-inventory snapshots into the graph — 1.5's fourth and
last named collector (`claude/ROADMAP-1.2-TO-2.0-2026-09-27.md` §
1.5), deferred past 1.5.0 (`ADR-0011` § 22's own closing note) and
cadré for 1.5.1, 2026-09-28.

**One subdirectory per subject, not one shared batch file — the same
reasoning `aistack.timemachine.projection.docker_digest` already gives
for its own write side (`aistack.providers.docker.packages_history`
explains it there).** This walk is the read side of the same
contract: it finds every subject root under `generated_dir /
"docker-packages"` by locating each `history/docker-packages` leaf,
however deep a subject's own `/` nests it, and rebuilds the subject
string the exact inverse way `aistack.providers.docker.packages_history
._output_path` derived it.

**`aistack:packageCount` and `aistack:packageMechanism`, not every
package, as graph facts.** A package inventory can hold anywhere from
zero to thousands of entries; promoting each one to its own graph
triple would turn a provenance graph meant to answer "when did this
happen, for which subject" into a bulk package manifest nothing here
queries that way — the same reasoning `aistack.timemachine.projection
.docker_diff`'s own module already gives for `aistack:changeCount`,
doubled here. The full name/version list stays exactly where it was
recorded — reachable through `aistack.cli.history_query` the same way
any other stream's raw content already is — and this stream's own two
lightweight facts (how many packages, which mechanism answered) are
what a graph fact is worth stating.

**No `aistack:occurredAt`, the same restraint every other 1.5 stream
in this package already documents for the same reason.** A package
inventory observed this cycle states only what is installed *now*,
never when any one package was itself installed or upgraded — there
is no independent instant here to state.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history import available_instants, format_instant, observation_at
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

# `aistack.providers.docker.packages_history`'s own leaf names,
# redeclared here — the same cross-boundary convention every other
# projector in this package already redeclares its own stream's leaf
# name under.
PACKAGES_DIRNAME = "docker-packages"
STEM = "docker-packages"
STREAM_STEM = "docker-packages"


@dataclass(frozen=True)
class DockerPackagesProjectionSummary:
    """What one `project_docker_packages` run actually did — the same
    measured-report shape every other stream's projection already
    gives a caller."""

    subjects_seen: int
    snapshots_seen: int
    facts_written: int
    facts_dropped: int


def _subject_roots(packages_root: Path) -> list[tuple[str, Path]]:
    """
    `(subject, subject_root)` for every subject `packages_root`
    actually holds a recorded observation for — the same `rglob`-based
    walk every other write-on-change stream's projector in this
    package already holds, unchanged in shape, against this stream's
    own leaf name.
    """

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

    One shared `prov:Activity` (`stream_iri("docker-packages")`) is
    the collection activity every snapshot is `prov:wasGeneratedBy` —
    emitted once, lazily, the first time this stream is actually found
    to hold a snapshot, the same guard every other dedicated projector
    in this package already holds.

    For each snapshot: it exists (`prov:Entity`), when it was recorded
    (`prov:generatedAtTime` — recording time; see this module's own
    docstring for why no `aistack:occurredAt`), which subject it
    concerns (`aistack:stableSubject`), how many packages it reported
    (`aistack:packageCount`), and which mechanism answered
    (`aistack:packageMechanism`).

    Every candidate fact passes through the same `filter_fact` every
    other stream's projection already uses.
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

        for instant in available_instants(subject_root, STEM):
            observation = observation_at(subject_root, STEM, instant)
            if observation is None:
                continue

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
