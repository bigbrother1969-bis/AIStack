"""
Package Manager — DefaultPackageManager.
"""

from __future__ import annotations

from pathlib import Path

from aistack.package_manager.contracts.knowledge_package import (
    KnowledgePackage,
)
from aistack.package_manager.interfaces.package_manager import (
    PackageManager,
)


class DefaultPackageManager(PackageManager):
    """
    Receive and inspect a KnowledgePackage. Holds no policy of its
    own — `ARCH-0013`: "The PackageManager does not replace governance
    decisions."
    """

    def receive(
        self,
        package: KnowledgePackage,
    ) -> KnowledgePackage:

        if not package.package_id:
            raise ValueError(
                "a KnowledgePackage must declare a package_id"
            )

        if not package.items:
            raise ValueError(
                f"package {package.package_id!r} carries no items"
            )

        for item in package.items:

            if not item.target_path:
                raise ValueError(
                    f"package {package.package_id!r} has an item "
                    "with an empty target_path"
                )

            if not item.content:
                raise ValueError(
                    f"package {package.package_id!r}, item "
                    f"{item.target_path!r}: empty content"
                )

        return package

    def inspect(
        self,
        package: KnowledgePackage,
        repository_root: Path,
    ) -> tuple[str, ...]:

        notes: list[str] = []

        for item in package.items:

            target = repository_root / item.target_path

            if not target.is_file():
                notes.append(
                    f"{item.target_path}: target file does not exist"
                )
                continue

            text = target.read_text(encoding="utf-8")

            if item.anchor is None:
                notes.append(
                    f"{item.target_path}: no anchor, "
                    "content would be appended at end of file"
                )
                continue

            occurrences = text.count(item.anchor)

            notes.append(
                f"{item.target_path}: anchor found "
                f"{occurrences} time(s)"
            )

        return tuple(notes)
