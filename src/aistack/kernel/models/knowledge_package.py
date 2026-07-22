from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgePackage:
    """
    Passive transport container for knowledge.

    Its identifier is the only mandatory invariant.
    It enables traceability, replay, rollback, and historization.
    """

    id: str
