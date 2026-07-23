from __future__ import annotations

from abc import ABC, abstractmethod

from aistack.kernel.knowledge import KnowledgePackage


class KnowledgeRepository(ABC):
    """
    Contract for storing governed knowledge artifacts.

    Knowledge persistence is independent
    from storage implementation.
    """

    @abstractmethod
    def store(
        self,
        package: KnowledgePackage,
    ) -> None:
        """
        Store a knowledge package.
        """
        pass

    @abstractmethod
    def get(
        self,
        identifier: str,
    ) -> KnowledgePackage | None:
        """
        Retrieve a knowledge package by identifier.
        """
        pass
