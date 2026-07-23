from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgePackage:
    """
    Immutable knowledge package.

    A KnowledgePackage is a portable container
    grouping governed knowledge artifacts.

    It is designed for export, transfer
    and reconstruction of AIStack knowledge heritage.
    """

    identifier: str
