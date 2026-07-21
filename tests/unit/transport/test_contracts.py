from aistack.transport.contracts import (
    DeliveryMode,
    ResourceReference,
    TransportEndpoint,
    TransportRequest,
)


def test_resource_reference() -> None:
    resource = ResourceReference(
        resource_type="file",
        resource_id="hello.txt",
    )

    assert resource.resource_type == "file"
    assert resource.resource_id == "hello.txt"


def test_transport_endpoint() -> None:
    endpoint = TransportEndpoint(
        endpoint_id="local",
        endpoint_type="filesystem",
        uri="/tmp",
    )

    assert endpoint.endpoint_id == "local"
    assert endpoint.endpoint_type == "filesystem"
    assert endpoint.uri == "/tmp"


def test_transport_request() -> None:
    request = TransportRequest(
        source_resource=ResourceReference(
            resource_type="file",
            resource_id="hello.txt",
        ),
        destination_resource=ResourceReference(
            resource_type="file",
            resource_id="copy.txt",
        ),
        source=TransportEndpoint(
            endpoint_id="source",
            endpoint_type="filesystem",
            uri="/source",
        ),
        destination=TransportEndpoint(
            endpoint_id="destination",
            endpoint_type="filesystem",
            uri="/destination",
        ),
        delivery_mode=DeliveryMode.REPLACE,
    )

    assert request.source_resource.resource_id == "hello.txt"
    assert request.destination_resource.resource_id == "copy.txt"
    assert request.source.endpoint_id == "source"
    assert request.destination.endpoint_id == "destination"
    assert request.delivery_mode is DeliveryMode.REPLACE


def test_delivery_mode() -> None:
    assert DeliveryMode.CREATE.value == "create"
    assert DeliveryMode.REPLACE.value == "replace"
