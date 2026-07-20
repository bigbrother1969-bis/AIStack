from __future__ import annotations

from aistack.transport.contracts import TransportRequest
from aistack.transport.interfaces.transport_engine import TransportEngine
from aistack.transport.interfaces.transport_registry import TransportRegistry


class DefaultTransportEngine(TransportEngine):
    """
    Default implementation of the Knowledge Transport Layer.
    """

    def __init__(self, registry: TransportRegistry) -> None:
        self._registry = registry

    def execute(self, request: TransportRequest) -> None:
        source_capability = self._registry.get(
            request.source.endpoint_type
        )

        destination_capability = self._registry.get(
            request.destination.endpoint_type
        )

        data = source_capability.receiver.receive(
            request.resource,
        )

        destination_capability.writer.write(
            request.resource,
            data,
        )

        destination_capability.verifier.verify(
            request,
        )
