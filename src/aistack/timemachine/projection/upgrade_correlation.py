"""
Project the upgrade correlation: link the package snapshots taken
before and after each image-digest change.

Trigger: `digest_history.record_image_digest` writes only on change,
so every recorded `docker-digest` instant after a subject's first is a
digest change; values are not compared again here.

Pairing: the last packages snapshot at or before the change and the
first one strictly after it, with no time window; a large gap stays
visible through the two entities' `prov:generatedAtTime`.

Only `aistack:upgradeCorrelatesWith` is written, between two
`docker-packages` entities that `project_docker_packages` already
emitted (run it first). Observations are re-validated with the same
shape checks as the digest and packages projectors, so no link points
at an entity they skipped.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

from aistack.history import format_instant, latest_observations
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import docker_packages_iri
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import AISTACK_UPGRADE_CORRELATES_WITH

# Leaf names of `aistack.providers.docker.digest_history` and
# `.packages_history`, redeclared rather than imported.
DIGEST_DIRNAME = "docker-digest"
DIGEST_STEM = "docker-digest"
PACKAGES_DIRNAME = "docker-packages"
PACKAGES_STEM = "docker-packages"


@dataclass(frozen=True)
class UpgradeCorrelationProjectionSummary:
    """What one `project_upgrade_correlation` run did."""

    subjects_seen: int
    digest_changes_seen: int
    correlations_written: int
    facts_written: int
    facts_dropped: int


def _subject_roots(root: Path, stem: str) -> dict[str, Path]:
    """
    `{subject: subject_root}` for every subject under `root` with a
    recorded `stem` observation, found by its `history/<stem>` leaf.
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
    """Instants of valid `{"digest": str}` observations, oldest first."""

    instants: list[datetime] = []
    for observation in latest_observations(subject_root, DIGEST_STEM):
        instant = observation.observed_at
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
    Instants of valid `{"mechanism": str, "packages": list}` snapshots,
    oldest first.
    """

    instants: list[datetime] = []
    for observation in latest_observations(subject_root, PACKAGES_STEM):
        instant = observation.observed_at
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
    `docker-packages` snapshot before and after each `docker-digest`
    change, for every subject both streams hold.

    Must run after `project_docker_digest` and
    `project_docker_packages`, which emit the linked entities. Every
    fact goes through `filter_fact`.
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
