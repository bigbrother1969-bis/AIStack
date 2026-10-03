"""
The persisted store for Explications — `ADR-0011` § *Decision* 7-8, the
Time Machine's fifth source and, per its own § 1, the projection's
eventual input alongside the four existing historicised streams.

**Foundation only, no real caller yet.** This module gives Explications
a place to live — serialize, persist, read back — the same "contract
before a real producer" step `aistack.timemachine.graph.GraphStore` and
`OxigraphGraphStore` were for the graph itself (patch 0049): declared,
tested against real (not fabricated) data, with nothing yet calling it
for a real reason. Importing the four real sources `ADR-0011` § 8 names
(commits, `pra_tests.yml`, the AI Runtime's own `explain` answers,
`claude/` notes) and projecting Explications into the graph are both
deferred to the patch that adds the first real source — building
either now, before a real source's own shape is in hand, would be
exactly the invented infrastructure `ARC-P-006` forbids.

**`KnowledgeArtifact` reused exactly, per `ADR-0011` § 7** — no new
contract. `id` is the subject an Explication explains (matching the
sentence "`id` names the subject explained"); `confidence` is
`Proposed`, the level `STD-0100` v2.12 adds for exactly this case (an
AI-authored or imported explanation nobody has read, sitting below
`Declared` because even `Declared`'s honest default presumes a human
author standing behind the claim). `aistack.contracts.artifact
.KnowledgeArtifact` deliberately carries no `version`/`provenance`
pair of its own (see that module's own comment on the second, unwired
definition merged out of existence 2026-09-18) — so nothing here
invents one; the historicised copy `write_artifact_with_history`
already keeps under `history/<subject>/` is the version ledger,
exactly as it already is for Traces, Décisions CPU and Raisonnements
IA. A correction or a human validation is simply another call to
`record_explication` for the same subject: the next entry in that
subject's own history, current through `explication_history_path`'s
stable "latest" path.

**One stream per subject, not one shared stream** — the same choice
`aistack.ai_runtime.reasoning_history` already made 2026-09-18 for
exactly the same reason: a subject's own Explications stay
independently versioned and queryable
(`aistack.cli.history_query`), rather than one growing file mixing
every subject the graph has ever had something said about.

**Not `aistack.contracts.artifact_builder.ArtifactBuilder`.** That
contract turns a `DiscoveryResult` — a governed document found on disk,
already carrying its own frontmatter — into a `KnowledgeArtifact`; it
is the Context Bundle's own registry pipeline (`aistack.context_bundle
.builders.artifact_builder`), already wired to a real, different
concern. An Explication is not a discovered document; forcing it
through a contract shaped for one would be the same "fifth mechanism
where a fourth one exists" the AI Reasoning History's own patch notes
warned against for a different case — no such fit exists here, so it
is not reused.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from aistack.history.subject_names import stem_for_subject
from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.generators.history import write_artifact_with_history
from aistack.history import latest_observations

# **Corrected before any real data ever existed at the old path** —
# patch 0054 declared this as `reports/generated/history/explications`,
# directly inside the top-level `history/` directory
# `aistack.timemachine.projection.project_observation_history` already
# scans via `available_stems(reports/generated)` for the four existing
# streams. Measured while building the first real importer (patch
# after 0054): that scan expects each entry under `history/` to itself
# be a stem's own flat timestamped-snapshot directory
# (`history/<stem>/<timestamp>.json`), not another subject-keyed layer
# (`history/explications/<subject>.json` plus *its own* nested
# `history/explications/history/<subject>/`) — the same shape mismatch
# `aistack.ai_runtime.reasoning_history` already has relative to that
# scan (see `from_ai_reasoning.py`'s own note). Explications is its own
# named stream, one file per subject, exactly like `ai-reasoning`
# already is: `reports/generated/explications/<subject>.json`, read by
# its own `available_stems`/`available_instants` call
# (`aistack.timemachine.projection.project_explications`) rather than
# folded into the generic four-stream scan. `reports/generated/` was
# never gitignored by exception for `history/` alone (`.gitignore` line
# 46 excludes the whole tree), so nothing on disk anywhere ever held
# data at the old path — this is a pre-launch correction, not a
# migration.
DEFAULT_OUTPUT_DIR = Path("reports/generated/explications")


def explication_history_path(
    subject: str, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> Path:
    """
    The stable "latest" path one subject's Explication history is read
    from and written to — `output_dir/<subject>.json`, the same
    per-subject convention Observation History and AI Reasoning
    History already use.
    """

    return output_dir / f"{stem_for_subject(subject)}.json"


def serialize_explication(artifact: KnowledgeArtifact) -> dict[str, Any]:
    """
    The JSON-safe shape one Explication is persisted as — every field
    `KnowledgeArtifact` declares, none dropped and none invented.
    `lifecycle`/`score` are left out: no real producer has populated
    either for an Explication yet, and `None` has nothing to
    round-trip through JSON as (FDN-0003 Article 12 says an undeclared
    value must stay visible, not that a field nobody has used yet must
    be serialized as a null placeholder).
    """

    return {
        "id": artifact.id,
        "title": artifact.title,
        "declared_type": artifact.declared_type,
        "domain": artifact.domain,
        "semantic_type": artifact.semantic_type,
        "criticality": artifact.criticality,
        "owner": artifact.owner,
        "source": artifact.source,
        "created_at": artifact.created_at.isoformat(),
        "updated_at": artifact.updated_at.isoformat(),
        "confidence": artifact.confidence,
        "status": artifact.status,
        "content": artifact.content,
        "metadata": artifact.metadata,
    }


def deserialize_explication(data: dict[str, Any]) -> KnowledgeArtifact:
    """
    The inverse of `serialize_explication` — reads back exactly what
    was written, defaulting only the two fields `KnowledgeArtifact`
    itself defaults (`confidence`/`status` to `UNDECLARED`, `content`
    to `""`), never inventing a value the artifact never declared.
    """

    return KnowledgeArtifact(
        id=data["id"],
        title=data["title"],
        declared_type=data["declared_type"],
        domain=data["domain"],
        semantic_type=data["semantic_type"],
        criticality=data["criticality"],
        owner=data["owner"],
        source=data["source"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        confidence=data.get("confidence", UNDECLARED),
        status=data.get("status", UNDECLARED),
        content=data.get("content", ""),
        metadata=data.get("metadata", {}),
    )


def record_explication(
    artifact: KnowledgeArtifact, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> Path:
    """
    Persist one Explication to its subject's own history stream.
    Returns the stable "latest" path written
    (`write_artifact_with_history`'s own convention) — the same return
    shape `aistack.ai_runtime.reasoning_history.record_ai_reasoning`
    already gives its own callers.
    """

    path = explication_history_path(artifact.id, output_dir)
    content = (
        json.dumps(serialize_explication(artifact), indent=2, ensure_ascii=False)
        + "\n"
    )

    latest_path, _ = write_artifact_with_history(content, path)

    return latest_path


def read_latest_explication(
    subject: str, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> KnowledgeArtifact | None:
    """
    The current Explication for `subject`, or `None` when nothing has
    ever been recorded for it — the same "no store yet is a real
    signal, not an error" shape `OxigraphGraphStore.read_only` gives a
    caller for the graph itself, so a future projection can tell
    "nothing here" from "something went wrong reading it".
    """

    path = explication_history_path(subject, output_dir)
    if not path.exists():
        return None

    return deserialize_explication(json.loads(path.read_text(encoding="utf-8")))


def read_explication_history(
    subject: str, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> list[KnowledgeArtifact]:
    """
    Every version of `subject`'s Explication ever recorded, oldest
    first — the full history `write_artifact_with_history` already
    keeps, not only the current one `read_latest_explication` reads.
    An importer uses this to tell "already recorded" from "new" (see
    `aistack.explications.from_ai_reasoning`'s own docstring) without
    a second, separate ledger of what it has already imported — the
    files already on disk are the only ledger, the same principle
    `aistack.kernel.time.next_version_from_history` already applies
    for versioning itself.
    """

    history: list[KnowledgeArtifact] = []
    for observation in latest_observations(output_dir, stem_for_subject(subject)):
        history.append(deserialize_explication(json.loads(observation.read())))

    return history
