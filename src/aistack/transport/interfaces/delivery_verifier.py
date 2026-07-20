"""
Knowledge Transport Layer - Delivery Verifier interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.transport_transaction import TransportTransaction


class DeliveryVerifier(Protocol):
    """
    Verifies the integrity of a delivered resource.
    """

    def verify(
        self,
        transaction: TransportTransaction,
    ) -> bool:
        """
        Return True if the delivery is valid.
        """
        ...
