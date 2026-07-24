from abc import ABC, abstractmethod

from aistack.contracts.discovery import DiscoveryResult
from aistack.contracts.knowledge_registry import KnowledgeRegistry


class RegistryBuilder(ABC):
    """
    Contract for building a Knowledge Registry from discovered sources.
    """

    @abstractmethod
    def build(
        self,
        discoveries: list[DiscoveryResult],
    ) -> KnowledgeRegistry:
        """
        Build a governed knowledge registry.
        """
        raise NotImplementedError
