"""
Default Knowledge Dispatcher.
"""

from __future__ import annotations

from aistack.knowledge.contracts.knowledge_artifact import (
    KnowledgeArtifact,
)
from aistack.transaction.contracts.transaction import (
    Transaction,
)
from aistack.transfer.interfaces.knowledge_dispatcher import (
    KnowledgeDispatcher,
)


class DefaultKnowledgeDispatcher(KnowledgeDispatcher):
    """
    Default implementation of the Knowledge Dispatcher.

    The dispatcher converts a Knowledge Artifact
    into a governed Transaction.
    """

    def build_transaction(
        self,
        artifact: KnowledgeArtifact,
    ) -> Transaction:
        """
        Build the transaction required
        to transfer the artifact.

        Routing rules will be implemented
        incrementally.
        """

        return Transaction(
            operations=[],
        )
