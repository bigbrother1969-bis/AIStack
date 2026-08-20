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

    # Governance classification — all three are qualifications.
    # Per FDN-0003 Article 4 they are declared by a human and
    # read by the pipeline, never inferred. "unknown" is a
    # governed state, not a missing value.
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
    confidence: str = "unknown"
    status: str = "draft"
    content: str = ""

    # Extensible metadata
    metadata: dict[str, Any] = field(default_factory=dict)
