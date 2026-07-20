"""
Knowledge Transport Layer - Transport Engine interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.transport_transaction import TransportTransaction


class TransportEngine(Protocol):
    """
    Executes a transport transaction.
    """

    def transport(
        self,
        transaction: TransportTransaction,
    ) -> TransportTransaction:
        """
        Execute the transport operation.
        """
        ...
