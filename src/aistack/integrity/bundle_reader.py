from datetime import datetime
from pathlib import Path
import json
import zipfile

from aistack.conformance.registry_serialization import (
    deserialize_registries,
)
from aistack.conformance.serialization import deserialize_inventory
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

    The contract inventory travels only in the archive, because
    it is a separate entry rather than part of `bundle.json`. A
    consumer holding the loose `bundle.json` therefore gets a
    bundle whose `contract_inventory` is `None` — the honest
    result, and the one a check must be able to tell apart from
    a heritage with no orphan contracts.
    """

    path = Path(path)

    inventory = None
    registries = None

    if zipfile.is_zipfile(path):

        with zipfile.ZipFile(path) as archive:
            payload = json.loads(
                archive.read("bundle.json")
            )

            if "contract-inventory.json" in archive.namelist():
                inventory = deserialize_inventory(
                    json.loads(
                        archive.read("contract-inventory.json")
                    )
                )

            if "registry-inventory.json" in archive.namelist():
                registries = deserialize_registries(
                    json.loads(
                        archive.read("registry-inventory.json")
                    )
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
            metadata={
                "content_hash": entry.get("content_hash", ""),
            },
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
        contract_inventory=inventory,
        registry_inventory=registries,
    )
