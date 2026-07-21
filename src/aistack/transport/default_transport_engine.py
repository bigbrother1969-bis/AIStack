from __future__ import annotations

from uuid import uuid4

from aistack.transport.contracts import (
    TransportRequest,
    TransportResult,
    TransportStatus,
)
from aistack.transport.interfaces.transport_engine import TransportEngine
from aistack.transport.interfaces.transport_registry import TransportRegistry


class DefaultTransportEngine(TransportEngine):
    """
    Default implementation of the Knowledge Transport Layer.
    """

    def __init__(self, registry: TransportRegistry) -> None:
        self._registry = registry

    def transport(
        self,
        request: TransportRequest,
    ) -> TransportResult:
        source_capability = self._registry.get(
            request.source.endpoint_type
        )

        destination_capability = self._registry.get(
            request.destination.endpoint_type
        )

        data = source_capability.receiver.receive(
            request.source_resource,
        )

        destination_capability.writer.write(
            request.destination_resource,
            data,
        )

        result = TransportResult(
            transaction_id=str(uuid4()),
            status=TransportStatus.DELIVERED,
            delivered=True,
            verified=False,
            rollback_available=False,
        )

        verified = destination_capability.verifier.verify(
            request,
            result,
        )

        return TransportResult(
            transaction_id=result.transaction_id,
            status=(
                TransportStatus.VERIFIED
                if verified
                else TransportStatus.DELIVERED
            ),
            delivered=True,
            verified=verified,
            rollback_available=False,
        )
