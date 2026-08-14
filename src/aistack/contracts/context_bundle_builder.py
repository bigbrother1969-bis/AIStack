from abc import ABC, abstractmethod

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.knowledge_registry import KnowledgeRegistry


class ContextBundleBuilder(ABC):
    """
    Contract for building a Context Bundle from a Knowledge Registry.
    """

    @abstractmethod
    def build(
        self,
        registry: KnowledgeRegistry,
        source_commit: str,
        repository_url: str = "unknown",
    ) -> ContextBundle:
        """
        Build a portable governed knowledge context.
        """
        raise NotImplementedError
