from __future__ import annotations

import pytest

from aistack.transaction.adapters.transport_operation_engine import (
    TransportOperationEngine,
)
from aistack.transport.contracts.delivery_mode import DeliveryMode
from aistack.transport.contracts.resource_reference import ResourceReference
from aistack.transport.contracts.transport_endpoint import TransportEndpoint
from aistack.transport.contracts.transport_request import TransportRequest


class FakeTransportEngine:
    def __init__(self) -> None:
        self.received_request: TransportRequest | None = None
        self.result = object()

    def transport(self, request: TransportRequest) -> object:
        self.received_request = request
        return self.result


def make_request() -> TransportRequest:
    return TransportRequest(
        source_resource=ResourceReference(
            resource_type="file",
            resource_id="example.bin",
        ),
        destination_resource=ResourceReference(
            resource_type="file",
            resource_id="example-copy.bin",
        ),
        source=TransportEndpoint(
            endpoint_id="source",
            endpoint_type="filesystem",
            uri="/tmp/source/example.bin",
        ),
        destination=TransportEndpoint(
            endpoint_id="destination",
            endpoint_type="filesystem",
            uri="/tmp/destination/example.bin",
        ),
        delivery_mode=DeliveryMode.CREATE,
    )


def test_execute_delegates_transport_request_to_transport_engine() -> None:
    transport_engine = FakeTransportEngine()
    adapter = TransportOperationEngine(transport_engine)

    request = make_request()

    result = adapter.execute(request)

    assert transport_engine.received_request is request
    assert result is transport_engine.result


def test_execute_rejects_non_transport_request_payload() -> None:
    adapter = TransportOperationEngine(FakeTransportEngine())

    with pytest.raises(
        TypeError,
        match="expects a TransportRequest payload",
    ):
        adapter.execute(object())
