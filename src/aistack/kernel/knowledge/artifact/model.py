from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.knowledge.artifact.lifecycle import (
    KnowledgeLifecycle,
)

from aistack.kernel.knowledge.artifact.provenance import (
    KnowledgeProvenance,
)

from aistack.kernel.knowledge.artifact.score import (
    KnowledgeScore,
)


@dataclass(frozen=True, slots=True)
class KnowledgeArtifact:
    """
    Governed knowledge artifact.

    A KnowledgeArtifact is the smallest
    governed unit of AIStack knowledge.
    """

    identifier: str

    artifact_type: str

    name: str

    provenance: KnowledgeProvenance

    owner: str

    score: KnowledgeScore

    lifecycle: KnowledgeLifecycle

    content: dict[str, object]
