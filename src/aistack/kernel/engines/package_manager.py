from __future__ import annotations

from aistack.kernel.models import KnowledgePackage


class PackageManager:
    """
    Transport Layer facade.

    The PackageManager orchestrates package capabilities.
    It never implements packaging algorithms itself.
    """

    def package(
        self,
        package: KnowledgePackage,
    ) -> KnowledgePackage:
        return package

    def unpackage(
        self,
        package: KnowledgePackage,
    ) -> KnowledgePackage:
        return package
