"""
Project recorded collection gaps into the graph (`ADR-0011` § 9).

Gaps live under their own root, `generated_dir / "collection-gaps" /
<stream_stem>` (see `aistack.generators.collection_gap`), not in the
stream's observation history. Each gap links to the stream's existing
activity (`stream_iri`); no second activity node is created.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from aistack.history import format_instant, latest_observations
from aistack.timemachine.graph import GraphStore, Literal
from aistack.timemachine.iri import collection_gap_iri, stream_iri
from aistack.timemachine.projection.filter import filter_fact
from aistack.timemachine.vocabulary import (
    AISTACK_COLLECTION_GAP,
    AISTACK_OCCURRED_AT,
    AISTACK_STABLE_SUBJECT,
    PROV_ENTITY,
    PROV_GENERATED_AT_TIME,
    PROV_WAS_GENERATED_BY,
    RDF_TYPE,
    XSD_DATE_TIME,
)

# Leaf name of `aistack.generators.collection_gap.DEFAULT_COLLECTION_GAPS_ROOT`,
# redeclared rather than imported across the writer/reader boundary.
COLLECTION_GAPS_DIRNAME = "collection-gaps"

# File stem `record_collection_gap` writes; one history file per gap.
STEM = "collection-gap"


@dataclass(frozen=True)
class CollectionGapsProjectionSummary:
    """What one `project_collection_gaps` run did."""

    streams_seen: int
    gaps_seen: int
    facts_written: int
    facts_dropped: int


def project_collection_gaps(
    store: GraphStore,
    generated_dir: Path = Path("reports/generated"),
    user_data_roots: Iterable[str] = (),
) -> CollectionGapsProjectionSummary:
    """
    Add every recorded collection gap under
    `generated_dir / "collection-gaps"` to `store`.

    Per gap: a `prov:Entity` whose `aistack:stableSubject` is the
    stream stem (gaps are per collector, not per container), generated
    by the stream's activity; `aistack:occurredAt` is when coverage was
    lost and `prov:generatedAtTime` when it resumed (the recording
    instant). The activity points at the gap via
    `aistack:collectionGap`.
    """

    gaps_root = generated_dir / COLLECTION_GAPS_DIRNAME

    streams_seen = 0
    gaps_seen = 0
    facts_written = 0
    facts_dropped = 0

    def emit(subject: str, predicate: str, obj: str | Literal) -> None:
        nonlocal facts_written, facts_dropped
        if filter_fact(subject, obj, user_data_roots):
            store.add(subject, predicate, obj)
            facts_written += 1
        else:
            facts_dropped += 1

    if not gaps_root.is_dir():
        return CollectionGapsProjectionSummary(0, 0, 0, 0)

    for stream_dir in sorted(path for path in gaps_root.iterdir() if path.is_dir()):
        stream_stem_name = stream_dir.name
        activity = stream_iri(stream_stem_name)
        streams_seen += 1

        for observation in latest_observations(stream_dir, STEM):
            instant = observation.observed_at

            parsed = json.loads(observation.read())
            if not isinstance(parsed, dict):
                continue
            start = parsed.get("start")
            if not isinstance(start, str):
                continue

            gaps_seen += 1
            instant_label = format_instant(instant)
            gap_entity = collection_gap_iri(stream_stem_name, instant_label)

            emit(gap_entity, RDF_TYPE, PROV_ENTITY)
            emit(gap_entity, PROV_WAS_GENERATED_BY, activity)
            emit(
                gap_entity,
                PROV_GENERATED_AT_TIME,
                Literal(instant.isoformat(), datatype=XSD_DATE_TIME),
            )
            emit(gap_entity, AISTACK_OCCURRED_AT, Literal(start, datatype=XSD_DATE_TIME))
            emit(gap_entity, AISTACK_STABLE_SUBJECT, Literal(stream_stem_name))
            emit(activity, AISTACK_COLLECTION_GAP, gap_entity)

    return CollectionGapsProjectionSummary(
        streams_seen=streams_seen,
        gaps_seen=gaps_seen,
        facts_written=facts_written,
        facts_dropped=facts_dropped,
    )
