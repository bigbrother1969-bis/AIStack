"""
Knowledge Packager interface.
"""

from __future__ import annotations

from typing import Protocol


class KnowledgePackager(Protocol):
    """
    Rebuilds the governed knowledge heritage
    after transports have completed.
    """

    def package(self) -> None:
        """
        Rebuild the knowledge package.
        """
        ...
