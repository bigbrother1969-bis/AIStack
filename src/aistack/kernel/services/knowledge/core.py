from __future__ import annotations

from dataclasses import dataclass

from aistack.kernel.services.knowledge.repository import (
    KnowledgeRepository,
)


@dataclass(frozen=True, slots=True)
class KnowledgeServices:
    """
    Services dedicated to governed knowledge lifecycle.

    This service boundary exposes knowledge
    persistence capabilities to the Kernel.
    """

    repository: KnowledgeRepository
