"""
Knowledge Transport Layer - Router interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.transport_request import TransportRequest


class Router(Protocol):
    """
    Resolves the transport strategy for a request.
    """

    def route(self, request: TransportRequest) -> str:
        """
        Return the identifier of the transport strategy.
        """
        ...
