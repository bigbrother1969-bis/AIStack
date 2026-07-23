from __future__ import annotations

from enum import Enum


class KnowledgeLifecycle(str, Enum):
    """
    Lifecycle state of a governed knowledge artifact.
    """

    DISCOVERED = "discovered"
    VALIDATED = "validated"
    ACTIVE = "active"
    ARCHIVED = "archived"
