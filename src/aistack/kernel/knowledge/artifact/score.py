from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeScore:
    """
    Trust evaluation of a knowledge artifact.
    """

    confidence: float
