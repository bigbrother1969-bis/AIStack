from __future__ import annotations

from abc import ABC, abstractmethod

from aistack.kernel.models import KnowledgePackage


class PackageCapability(ABC):
    """
    Contract implemented by all Package Capabilities.
    """

    @abstractmethod
    def supports(
        self,
        package: KnowledgePackage,
    ) -> bool:
        """
        Return True if this capability supports the package.
        """

    @abstractmethod
    def process(
        self,
        package: KnowledgePackage,
    ) -> KnowledgePackage:
        """
        Process the package and return the resulting package.
        """
