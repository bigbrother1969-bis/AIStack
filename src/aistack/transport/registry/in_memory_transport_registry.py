"""
In-memory implementation of the Knowledge Transport Layer registry.
"""

from __future__ import annotations

from aistack.transport.capabilities.transport_capability import (
    TransportCapability,
)


class InMemoryTransportRegistry:
    """
    Stores transport capabilities indexed by endpoint type.
    """

    def __init__(self) -> None:
        self._capabilities: dict[str, TransportCapability] = {}

    def register(
        self,
        endpoint_type: str,
        capability: TransportCapability,
    ) -> None:
        """
        Register a transport capability for an endpoint type.
        """
        if not endpoint_type:
            raise ValueError("endpoint_type must not be empty")

        if endpoint_type in self._capabilities:
            raise ValueError(
                f"Transport capability already registered: {endpoint_type}"
            )

        self._capabilities[endpoint_type] = capability

    def get(
        self,
        endpoint_type: str,
    ) -> TransportCapability:
        """
        Return the capability registered for an endpoint type.
        """
        try:
            return self._capabilities[endpoint_type]
        except KeyError as error:
            raise LookupError(
                f"No transport capability registered: {endpoint_type}"
            ) from error
