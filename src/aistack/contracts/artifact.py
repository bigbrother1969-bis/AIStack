from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aistack.contracts.knowledge_lifecycle import KnowledgeLifecycle
from aistack.contracts.knowledge_score import KnowledgeScore
from aistack.contracts.undeclared import UNDECLARED


@dataclass(frozen=True)
class KnowledgeArtifact:
    """
    Immutable governed knowledge artifact: identity, provenance,
    classification, governance metadata and lifecycle.

    No field defaults to an invented value: where a default exists it is
    UNDECLARED, so "not stated" stays visible. The four classification
    fields have no default, so a producer must qualify each explicitly.
    """

    # The identifier the artifact declares (e.g. `ADR-0001`); other
    # artifacts cite it. The content hash lives in
    # `metadata["content_hash"]`. No declared identifier gives `unknown`.
    id: str
    title: str

    # Classification, declared by a human, never inferred.
    # `declared_type` is the artifact's free label; `semantic_type` is a
    # closed vocabulary, kept separate.
    declared_type: str
    domain: str
    semantic_type: str
    criticality: str

    # Ownership and provenance
    owner: str
    source: str

    # Lifecycle
    created_at: datetime
    updated_at: datetime

    # Confidence and lifecycle state
    confidence: str = UNDECLARED
    status: str = UNDECLARED
    content: str = ""

    # Extensible metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    # `None` when not staged or scored: a default stage or a zero
    # confidence would assert a measurement nobody made.
    lifecycle: KnowledgeLifecycle | None = None
    score: KnowledgeScore | None = None
