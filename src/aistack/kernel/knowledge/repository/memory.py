from __future__ import annotations

from aistack.kernel.knowledge import KnowledgeArtifact

from aistack.kernel.knowledge.repository.contract import (
    KnowledgeArtifactRepository,
)


class InMemoryKnowledgeArtifactRepository(
    KnowledgeArtifactRepository,
):
    """
    In-memory Knowledge Artifact repository.
    """

    def __init__(self) -> None:
        self._artifacts: dict[str, KnowledgeArtifact] = {}

    def save(
        self,
        artifact: KnowledgeArtifact,
    ) -> None:
        self._artifacts[
            artifact.identifier
        ] = artifact

    def get(
        self,
        identifier: str,
    ) -> KnowledgeArtifact:
        return self._artifacts[
            identifier
        ]

    def list(
        self,
    ) -> tuple[KnowledgeArtifact, ...]:
        return tuple(
            self._artifacts.values()
        )
