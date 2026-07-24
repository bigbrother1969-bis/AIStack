from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class KnowledgeArtifact:
    """
    Immutable representation of a governed AIStack knowledge artifact.

    A Knowledge Artifact is the fundamental unit of governed knowledge
    managed by AIStack.

    The artifact contains:
    - identity;
    - provenance;
    - classification;
    - governance metadata;
    - lifecycle information.
    """

    id: str
    title: str

    # Governance classification
    domain: str
    semantic_type: str
    criticality: int

    # Ownership and provenance
    owner: str
    source: str

    # Lifecycle
    created_at: datetime
    updated_at: datetime

    # Confidence and lifecycle state
    confidence: str = "unknown"
    status: str = "draft"
    content: str = ""

    # Extensible metadata
    metadata: dict[str, Any] = field(default_factory=dict)
