"""
Knowledge Transport Layer - Transport Engine interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.transport_request import TransportRequest
from aistack.transport.contracts.transport_result import TransportResult


class TransportEngine(Protocol):
    """
    Executes a transport request.
    """

    def transport(
        self,
        request: TransportRequest,
    ) -> TransportResult:
        """
        Execute the transport operation and return its result.
        """
        ...
