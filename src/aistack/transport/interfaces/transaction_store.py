"""
Knowledge Transport Layer - Transaction Store interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.transport_transaction import TransportTransaction


class TransactionStore(Protocol):
    """
    Stores the current state of transport transactions.
    """

    def save(
        self,
        transaction: TransportTransaction,
    ) -> None:
        ...

    def load(
        self,
        transaction_id: str,
    ) -> TransportTransaction:
        ...
