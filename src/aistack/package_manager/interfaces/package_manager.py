"""
Package Manager — PackageManager interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from aistack.package_manager.contracts.knowledge_package import (
    KnowledgePackage,
)


class PackageManager(ABC):
    """
    Contract for the receiving dock of a KnowledgePackage.

    `ARCH-0013`, verbatim: "The PackageManager coordinates knowledge
    package operations. Responsibilities: Receive Knowledge Packages.
    Inspect package content. Resolve available capabilities.
    Orchestrate validation and integration workflows. The
    PackageManager does not replace governance decisions."

    This interface covers the first two responsibilities only —
    receive and inspect. Resolving capabilities and orchestrating the
    validation/integration workflow is left to the caller (see
    `scripts/apply_arch0009_arch0013_cross_reference.py` for the first
    real orchestration), rather than building a generic orchestrator
    ahead of a second real case to generalize from.
    """

    @abstractmethod
    def receive(
        self,
        package: KnowledgePackage,
    ) -> KnowledgePackage:
        """
        Accept a KnowledgePackage as structurally well-formed.

        Raises `ValueError` if the package is malformed (no items, or
        an item with an empty target path or content) — a malformed
        package is rejected before it is ever inspected, not silently
        tolerated.
        """

        raise NotImplementedError

    @abstractmethod
    def inspect(
        self,
        package: KnowledgePackage,
        repository_root: Path,
    ) -> tuple[str, ...]:
        """
        Observe each item against the repository, without judgment.

        Returns one human-readable note per item: whether its target
        file exists, and how many times its anchor (if any) occurs.
        Inspection reports facts; whether those facts make the package
        acceptable is `ValidationEngine`'s responsibility, not this
        one's — `ARCH-0013` keeps the two separate.
        """

        raise NotImplementedError
