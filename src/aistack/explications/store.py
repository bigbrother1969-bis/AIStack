"""
The persisted store for Explications (`ADR-0011` § 7-8), the Time
Machine's explanation source.

An Explication is a `KnowledgeArtifact` whose `id` is the subject it
explains; an AI-authored or imported one has `confidence` `Proposed`.
There is no version field: the timestamped copies
`write_artifact_with_history` keeps are the version history, and a
correction or validation is another `record_explication` call for the
same subject.

One stream per subject, so each subject's Explications are versioned
independently.
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
from aistack.history import every_version

# Outside `reports/generated/history/`: the generic scan there expects
# flat `<stem>/<timestamp>` directories, not a subject-keyed layer.
# Read by `aistack.timemachine.projection.project_explications`.
DEFAULT_OUTPUT_DIR = Path("reports/generated/explications")


def explication_history_path(
    subject: str, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> Path:
    """The stable "latest" path of a subject's Explications: `output_dir/<subject>.json`."""

    return output_dir / f"{stem_for_subject(subject)}.json"


def serialize_explication(artifact: KnowledgeArtifact) -> dict[str, Any]:
    """
    The JSON-safe shape an Explication is persisted as. `lifecycle` and
    `score` are left out: nothing sets them for an Explication.
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
    The inverse of `serialize_explication`. Only `confidence`/`status`
    (to `UNDECLARED`), `content` and `metadata` have defaults.
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
    Persist one Explication to its subject's history stream and return
    the stable "latest" path.
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
    The current Explication for `subject`, or `None` when nothing was
    ever recorded for it.
    """

    path = explication_history_path(subject, output_dir)
    if not path.exists():
        return None

    return deserialize_explication(json.loads(path.read_text(encoding="utf-8")))


def read_explication_history(
    subject: str, output_dir: Path = DEFAULT_OUTPUT_DIR
) -> list[KnowledgeArtifact]:
    """
    Every recorded version of `subject`'s Explication, oldest first.
    Importers use it to skip what they already recorded.
    """

    history: list[KnowledgeArtifact] = []
    # Every version, including two written in the same second.
    for observation in every_version(output_dir, stem_for_subject(subject)):
        history.append(deserialize_explication(json.loads(observation.read())))

    return history
