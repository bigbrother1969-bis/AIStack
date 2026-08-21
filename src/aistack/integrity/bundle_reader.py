from datetime import datetime
from pathlib import Path
import json
import zipfile

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.classification import (
    normalize_domain,
    normalize_semantic_type,
)
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.criticality import normalize_criticality
from aistack.contracts.undeclared import UNDECLARED


def read_bundle(path: Path) -> ContextBundle:
    """
    Rebuild a ContextBundle from a published projection.

    The reader accepts either the bundle archive or the
    `bundle.json` it contains, so that any consumer holding
    only a bundle can verify it without access to the
    repository.

    Qualifications are normalized on the way in, exactly as the
    builder normalizes them on the way out. A projection
    produced by an older pipeline, or edited by hand, cannot
    introduce a criticality, a domain or a semantic type that
    the governed vocabularies do not contain.
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
            domain=normalize_domain(
                entry.get("domain")
            ),
            semantic_type=normalize_semantic_type(
                entry.get("semantic_type")
            ),
            criticality=normalize_criticality(
                entry.get("criticality")
            ),
            declared_type=entry.get("type", UNDECLARED),
            owner=entry.get("owner", UNDECLARED),
            source=entry["source"],
            content=entry.get("content", ""),
            status=entry.get("status", UNDECLARED),
            confidence=entry.get("confidence", UNDECLARED),
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
