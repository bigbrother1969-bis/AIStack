"""
Knowledge Transport Layer - Rollback Manager interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.transport_transaction import TransportTransaction


class RollbackManager(Protocol):
    """
    Rolls back a transport transaction.
    """

    def rollback(
        self,
        transaction: TransportTransaction,
    ) -> TransportTransaction:
        ...
