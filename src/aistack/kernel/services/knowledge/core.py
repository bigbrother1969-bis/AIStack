from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.knowledge.repository import (
    KnowledgeArtifactRepository,
)


@dataclass(frozen=True, slots=True)
class KnowledgeServices:
    """
    Kernel services exposing governed knowledge capabilities.
    """

    repository: KnowledgeArtifactRepository
