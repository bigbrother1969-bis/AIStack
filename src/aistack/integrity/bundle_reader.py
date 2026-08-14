from datetime import datetime
from pathlib import Path
import json
import zipfile

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle


def read_bundle(path: Path) -> ContextBundle:
    """
    Rebuild a ContextBundle from a published projection.

    The reader accepts either the bundle archive or the
    `bundle.json` it contains, so that any consumer holding
    only a bundle can verify it without access to the
    repository.
    """

    path = Path(path)

    if zipfile.is_zipfile(path):

        with zipfile.ZipFile(path) as archive:
            payload = json.loads(
                archive.read("bundle.json")
            )

    else:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )

    generated_at = datetime.fromisoformat(
        payload["generated_at"]
    )

    artifacts = [
        KnowledgeArtifact(
            id=entry["id"],
            title=entry["title"],
            domain=entry["domain"],
            semantic_type=entry["semantic_type"],
            criticality=entry["criticality"],
            owner=entry.get("owner", "unknown"),
            source=entry["source"],
            content=entry.get("content", ""),
            status=entry.get("status", "unknown"),
            confidence=entry.get("confidence", "unknown"),
            created_at=generated_at,
            updated_at=generated_at,
        )
        for entry in payload["artifacts"]
    ]

    return ContextBundle(
        id=payload["id"],
        title=payload["title"],
        generated_at=generated_at,
        source_commit=payload["source_commit"],
        artifacts=artifacts,
    )
