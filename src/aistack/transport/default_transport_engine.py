from __future__ import annotations

from uuid import uuid4

from aistack.transport.delivery_verifier import (
    DeliveryVerifier,
)
from aistack.transport.contracts import (
    DeliveryMode,
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

    def __init__(
        self,
        registry: TransportRegistry,
        delivery_verifier: DeliveryVerifier,
    ) -> None:
        self._registry = registry
        self._delivery_verifier = delivery_verifier

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

        if (
            request.delivery_mode is DeliveryMode.CREATE
            and destination_capability.writer.exists(
                request.destination_resource
            )
        ):
            return TransportResult(
                transaction_id=str(uuid4()),
                status=TransportStatus.FAILED,
                delivered=False,
                verified=False,
                rollback_available=False,
            )

        with source_capability.receiver.open(
            request.source_resource,
        ) as stream:
            destination_capability.writer.write(
                request.destination_resource,
                stream,
            )

        result = TransportResult(
            transaction_id=str(uuid4()),
            status=TransportStatus.DELIVERED,
            delivered=True,
            verified=False,
            rollback_available=False,
        )

        verified = self._delivery_verifier.verify(
            destination_capability,
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
