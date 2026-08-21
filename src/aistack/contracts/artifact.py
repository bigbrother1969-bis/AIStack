from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aistack.contracts.undeclared import UNDECLARED


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

    No field ever defaults to an invented value. Where a default
    exists it is UNDECLARED, because FDN-0003 Article 12 makes
    "the human has not said" a governed state that must remain
    representable and visible.

    The four classification fields carry no default at all. A
    producer that has qualified nothing must say so explicitly,
    field by field. That is deliberate friction: it is how a
    producer discovers it is about to emit unqualified knowledge,
    instead of emitting it silently.
    """

    id: str
    title: str

    # Governance classification — all four are qualifications.
    # Per FDN-0003 Article 4 they are declared by a human and
    # read by the pipeline, never inferred.
    #
    # `declared_type` is the free descriptive label the artifact
    # gives itself — "Foundation Manifesto", "Component README".
    # STD-0100 v2.0 keeps it distinct from `semantic_type`, which
    # is a closed vocabulary: collapsing them would either
    # destroy this wording or open that vocabulary.
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
