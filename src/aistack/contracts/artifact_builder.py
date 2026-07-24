from abc import ABC, abstractmethod

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.discovery import DiscoveryResult


class ArtifactBuilder(ABC):
    """
    Contract for transforming discovered sources into knowledge artifacts.
    """

    @abstractmethod
    def build(
        self,
        discovery: DiscoveryResult,
    ) -> KnowledgeArtifact:
        """
        Build a governed knowledge artifact from an observed source.
        """
        raise NotImplementedError
