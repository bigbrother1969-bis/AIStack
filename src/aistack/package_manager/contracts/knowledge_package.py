"""
Package Manager — KnowledgePackage contract.
"""

from __future__ import annotations

from dataclasses import dataclass

from aistack.package_manager.contracts.package_item import PackageItem


@dataclass(frozen=True, slots=True)
class KnowledgePackage:
    """
    A temporary container carrying proposed changes to the governed
    heritage — `ARCH-0013`'s KnowledgePackage.

    A KnowledgePackage is not a Single Point Of Truth. It exists to
    move a proposed change from wherever it was produced to the
    receiving dock (`PackageManager`); the repository remains the
    SPOT once the change is integrated.

    A Context Bundle (`aistack.context_bundle`) is one example of a
    KnowledgePackage — a package whose content happens to be a
    complete projection of the governed heritage. This package_id is
    deliberately generic: a KnowledgePackage carrying two small
    documentation items is exactly as valid a package as a full
    Context Bundle, and validation treats both the same way, one item
    at a time.
    """

    package_id: str

    title: str

    source: str

    items: tuple[PackageItem, ...]
