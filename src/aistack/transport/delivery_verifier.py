from __future__ import annotations

from aistack.transport.capabilities.transport_capability import (
    TransportCapability,
)
from aistack.transport.contracts import (
    TransportRequest,
    TransportResult,
)


class DeliveryVerifier:
    """
    Default delivery verifier.

    V1:
    A delivery is considered successful when the destination
    resource is observable.
    """

    def verify(
        self,
        capability: TransportCapability,
        request: TransportRequest,
        result: TransportResult,
    ) -> bool:
        return capability.writer.exists(
            request.destination_resource,
        )
