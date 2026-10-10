from __future__ import annotations

from aistack.transport.capabilities.transport_capability import (
    TransportCapability,
)
from aistack.transport.contracts import (
    TransportRequest,
    TransportResult,
)


class DeliveryVerifier:
    """Default delivery verifier: a delivery succeeds when the destination
    resource exists."""

    def verify(
        self,
        capability: TransportCapability,
        request: TransportRequest,
        result: TransportResult,
    ) -> bool:
        return capability.writer.exists(
            request.destination_resource,
        )
