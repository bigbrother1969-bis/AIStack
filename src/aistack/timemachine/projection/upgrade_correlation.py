"""
Project the "upgrade correlation" the 1.5.1 GUI cadrage named —
`ADR-0011` § 22's own closing note left the trigger cadré but the
design open; cadré and built here, 2026-09-28.

**Trigger: an image-digest change alone — cadrage decision 4
(`AskUserQuestion`, this segment's earlier turn).** No destroy+create
event pair is required. `aistack.providers.docker.digest_history
.record_image_digest` already writes only on change (write-on-change,
the same contract every 1.5 stream holds — see that module's own
docstring). So every recorded `docker-digest` instant for a subject
*after* its own first is, by that write-on-change contract alone,
already a genuine digest change. This module never re-opens a digest
observation's own value to compare it against the previous one — the
comparison already happened once, at collection time, and repeating
it here would only re-derive a fact `digest_history` already
established.

**Pairing: nearest on each side, no time window — cadrage decision 5
(`AskUserQuestion`, this segment).** For each digest-change instant,
the "before" packages snapshot is the last one recorded at or before
that instant; "after" is the first one recorded strictly after it —
always the nearest, however large the real gap turns out to be.
`ARC-P-006`: inventing a bounded window (a day, an hour) with no real
measured data yet to size it would be exactly the speculative
infrastructure that rule forbids. An unusually large real gap stays a
visible, measurable fact once the graph is queried (the two entities'
own `prov:generatedAtTime` subtract), never a threshold silently
hiding it.

**One new predicate, no new entity or activity — cadrage decision 1.**
`aistack:upgradeCorrelatesWith` links one already-projected
`docker-packages` entity (the "before" snapshot) to another (the
"after" snapshot) — both already exist as `prov:Entity` facts from
`project_docker_packages`, which this module's own caller must
therefore run first. No new `prov:Activity` is minted: this is a
relationship between two already-collected facts, not a new
collection stream of its own — the same restraint `aistack
:partOf`/`aistack:explains` already hold for a predicate that links
existing entities rather than announcing a new kind of collection.

**Only a snapshot this module can itself validate is ever
referenced.** The same shapes `project_docker_digest` and
`project_docker_packages` themselves require before emitting an
entity (`{"digest": str}`; `{"mechanism": str, "packages": list}`)
are re-checked here before an instant is treated as a candidate — the
same redundant-validation convention every projector in this package
already holds, so this module never links to an IRI the stream's own
projector declined to emit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from aistack.history import available_instants, format_instant, observation_at
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import docker_packages_iri
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import AISTACK_UPGRADE_CORRELATES_WITH

# Cross-boundary redeclarations, the same convention every other
# projector in this package already holds against its own stream's
# leaf names (`aistack.providers.docker.digest_history`/
# `.packages_history` own both).
DIGEST_DIRNAME = "docker-digest"
DIGEST_STEM = "docker-digest"
PACKAGES_DIRNAME = "docker-packages"
PACKAGES_STEM = "docker-packages"


@dataclass(frozen=True)
class UpgradeCorrelationProjectionSummary:
    """What one `project_upgrade_correlation` run actually did — the
    same measured-report shape every other projection in this package
    already gives a caller."""

    subjects_seen: int
    digest_changes_seen: int
    correlations_written: int
    facts_written: int
    facts_dropped: int


def _subject_roots(root: Path, stem: str) -> dict[str, Path]:
    """
    `{subject: subject_root}` for every subject `root` actually holds
    a recorded observation for — the same `rglob`-based walk every
    other write-on-change stream's projector in this package already
    holds, parameterised over `stem` so one function serves both the
    digest and the packages side rather than two near-identical
    copies (neither of which this module owns — see
    `aistack.timemachine.projection.docker_digest._subject_roots` and
    `.docker_packages._subject_roots` for the two originals this
    generalises).
    """

    roots: dict[str, Path] = {}

    for history_leaf in sorted(root.rglob(f"history/{stem}")):
        if not history_leaf.is_dir():
            continue

        subject_root = history_leaf.parent.parent
        subject = subject_root.relative_to(root).as_posix()
        roots[subject] = subject_root

    return roots


def _valid_digest_instants(subject_root: Path) -> list[datetime]:
    """
    Every instant this subject's own `docker-digest` history holds a
    validly-shaped observation for (`{"digest": str}`) — the same
    parse `aistack.timemachine.projection.docker_digest` itself
    requires before emitting an entity. Oldest first
    (`available_instants`'s own documented contract).
    """

    instants: list[datetime] = []
    for instant in available_instants(subject_root, DIGEST_STEM):
        observation = observation_at(subject_root, DIGEST_STEM, instant)
        if observation is None:
            continue
        try:
            parsed = json.loads(observation.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(parsed, dict):
            continue
        if not isinstance(parsed.get("digest"), str):
            continue
        instants.append(instant)

    return instants


def _valid_packages_instants(subject_root: Path) -> list[datetime]:
    """
    Every instant this subject's own `docker-packages` history holds a
    validly-shaped snapshot for (`{"mechanism": str, "packages":
    list}`) — the same parse `aistack.timemachine.projection
    .docker_packages` itself requires before emitting an entity.
    Oldest first, the same contract `_valid_digest_instants` already
    relies on.
    """

    instants: list[datetime] = []
    for instant in available_instants(subject_root, PACKAGES_STEM):
        observation = observation_at(subject_root, PACKAGES_STEM, instant)
        if observation is None:
            continue
        try:
            parsed = json.loads(observation.read())
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(parsed, dict):
            continue
        if not isinstance(parsed.get("mechanism"), str):
            continue
        if not isinstance(parsed.get("packages"), list):
            continue
        instants.append(instant)

    return instants


def _nearest_before(instants: list[datetime], change_instant: datetime) -> datetime | None:
    """The last of `instants` (oldest first) at or before
    `change_instant`, or `None` when none qualifies."""

    before: datetime | None = None
    for candidate in instants:
        if candidate <= change_instant:
            before = candidate
        else:
            break
    return before


def _nearest_after(instants: list[datetime], change_instant: datetime) -> datetime | None:
    """The first of `instants` (oldest first) strictly after
    `change_instant`, or `None` when none qualifies."""

    for candidate in instants:
        if candidate > change_instant:
            return candidate
    return None


def project_upgrade_correlation(
    store: GraphStore,
    generated_dir: Path = Path("reports/generated"),
    user_data_roots: Iterable[str] = (),
) -> UpgradeCorrelationProjectionSummary:
    """
    Add `aistack:upgradeCorrelatesWith` between the nearest
    `docker-packages` snapshot before and after each detected
    `docker-digest` change, for every subject both streams hold
    observations for.

    **Must run after both `project_docker_digest` and
    `project_docker_packages`** in any rebuild — see this module's
    own docstring for why: the two entities a correlation links
    already have to exist as `prov:Entity` facts before this module
    can link them.

    Every candidate fact passes through the same `filter_fact` every
    other stream's projection already uses.
    """

    digest_root = generated_dir / DIGEST_DIRNAME
    packages_root = generated_dir / PACKAGES_DIRNAME

    subjects_seen = 0
    digest_changes_seen = 0
    correlations_written = 0
    facts_written = 0
    facts_dropped = 0

    def emit(subject: str, predicate: str, obj: str | Literal) -> None:
        nonlocal facts_written, facts_dropped
        if filter_fact(subject, obj, user_data_roots):
            store.add(subject, predicate, obj)
            facts_written += 1
        else:
            facts_dropped += 1

    if not digest_root.is_dir() or not packages_root.is_dir():
        return UpgradeCorrelationProjectionSummary(0, 0, 0, 0, 0)

    digest_subjects = _subject_roots(digest_root, DIGEST_STEM)
    packages_subjects = _subject_roots(packages_root, PACKAGES_STEM)

    for subject_name in sorted(set(digest_subjects) & set(packages_subjects)):
        digest_instants = _valid_digest_instants(digest_subjects[subject_name])
        if len(digest_instants) < 2:
            continue  # no change ever recorded for this subject yet

        packages_instants = _valid_packages_instants(packages_subjects[subject_name])
        if not packages_instants:
            continue

        subjects_seen += 1

        for change_instant in digest_instants[1:]:  # every instant but the first
            digest_changes_seen += 1

            before = _nearest_before(packages_instants, change_instant)
            after = _nearest_after(packages_instants, change_instant)
            if before is None or after is None:
                continue

            before_entity = docker_packages_iri(subject_name, format_instant(before))
            after_entity = docker_packages_iri(subject_name, format_instant(after))

            emit(before_entity, AISTACK_UPGRADE_CORRELATES_WITH, after_entity)
            correlations_written += 1

    return UpgradeCorrelationProjectionSummary(
        subjects_seen=subjects_seen,
        digest_changes_seen=digest_changes_seen,
        correlations_written=correlations_written,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )
