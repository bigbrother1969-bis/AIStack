"""
Knowledge Transport Layer - Redelivery Manager interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.transport_transaction import TransportTransaction


class RedeliveryManager(Protocol):
    """
    Re-executes a transport transaction.
    """

    def redeliver(
        self,
        transaction: TransportTransaction,
    ) -> TransportTransaction:
        ...
