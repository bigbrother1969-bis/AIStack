"""
Knowledge Transport Layer - Delivery Verifier interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.transport_request import TransportRequest
from aistack.transport.contracts.transport_result import TransportResult


class DeliveryVerifier(Protocol):
    """
    Verifies the integrity of a transport result.
    """

    def verify(
        self,
        request: TransportRequest,
        result: TransportResult,
    ) -> bool:
        """
        Return True if the delivery is valid.
        """
        ...
