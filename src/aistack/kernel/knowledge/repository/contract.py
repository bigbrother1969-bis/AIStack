from __future__ import annotations

from abc import ABC, abstractmethod

from aistack.kernel.knowledge import KnowledgeArtifact


class KnowledgeArtifactRepository(ABC):
    """
    Repository contract for governed knowledge artifacts.

    Persistence responsibility only.
    Governance rules remain outside.
    """

    @abstractmethod
    def save(
        self,
        artifact: KnowledgeArtifact,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get(
        self,
        identifier: str,
    ) -> KnowledgeArtifact:
        raise NotImplementedError

    @abstractmethod
    def list(
        self,
    ) -> tuple[KnowledgeArtifact, ...]:
        raise NotImplementedError
