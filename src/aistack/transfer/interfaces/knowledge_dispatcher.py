"""
Knowledge Transfer - Dispatcher interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.knowledge.contracts.knowledge_artifact import (
    KnowledgeArtifact,
)
from aistack.transaction.contracts.transaction import (
    Transaction,
)


class KnowledgeDispatcher(Protocol):
    """
    Builds the transaction required to transfer
    a Knowledge Artifact.
    """

    def build_transaction(
        self,
        artifact: KnowledgeArtifact,
    ) -> Transaction:
        """
        Build the transaction required
        to transfer the artifact.
        """
        ...
