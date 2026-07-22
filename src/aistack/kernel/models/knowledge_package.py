from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgePackage:
    """
    Transportable package of governed knowledge.

    The internal representation will evolve incrementally.
    """
