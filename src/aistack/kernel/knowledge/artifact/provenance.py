from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeProvenance:
    """
    Origin information of a knowledge artifact.

    Every knowledge artifact must expose
    where it comes from.
    """

    source: str
    provider: str
