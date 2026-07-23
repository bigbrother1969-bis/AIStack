from __future__ import annotations

from dataclasses import dataclass, field

from aistack.kernel.knowledge import KnowledgePackage
from aistack.kernel.services.knowledge.repository import (
    KnowledgeRepository,
)


@dataclass
class InMemoryKnowledgeRepository(
    KnowledgeRepository
):
    """
    In-memory implementation of KnowledgeRepository.

    First implementation used by Kernel composition
    and unit tests.
    """

    packages: dict[str, KnowledgePackage] = field(
        default_factory=dict,
    )

    def store(
        self,
        package: KnowledgePackage,
    ) -> None:
        self.packages[package.identifier] = package

    def get(
        self,
        identifier: str,
    ) -> KnowledgePackage | None:
        return self.packages.get(identifier)
