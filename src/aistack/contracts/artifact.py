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

    # The governed identifier the artifact declares — `FDN-0003`,
    # `STD-0100`, `OPS-0001`. It is the only name anything else
    # cites: `relations.references` points at it, and a reader
    # asking the registry for a document asks by this.
    #
    # It held the **content hash** until 2026-08-23, and no
    # comment said so — this field was the one field of this
    # contract without one. The consequence was measured rather
    # than argued: a check comparing declared references against
    # it reported 85 dangling references on a heritage that had
    # none, and no consumer of a bundle could resolve `FDN-0003`
    # without parsing 65 frontmatter blocks (GOV-0002/OS-021).
    #
    # The hash is not lost. It lives in `metadata["content_hash"]`,
    # which is where the bundle fingerprint reads it from — the
    # fingerprint must stay derived from content, or two bundles
    # carrying the same names over different text would prove
    # equivalent.
    #
    # An artifact declaring no identifier carries `unknown`, per
    # FDN-0003 Article 12. A hash here would look like an identity
    # and would not be one.
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
