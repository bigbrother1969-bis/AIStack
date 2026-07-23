from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgePackage:
    """
    Immutable governed knowledge artifact.

    A KnowledgePackage is the minimal unit
    managed by AIStack Knowledge Services.
    """

    identifier: str
