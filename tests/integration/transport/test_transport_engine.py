from pathlib import Path

from aistack.path.filesystem import (
    FilesystemLocationRepository,
    FilesystemLocationResolver,
)
from aistack.transport.capabilities import FilesystemTransportCapability
from aistack.transport.contracts import (
    DeliveryMode,
    ResourceReference,
    TransportEndpoint,
    TransportRequest,
    TransportResult,
    TransportStatus,
)
from aistack.transport.default_transport_engine import (
    DefaultTransportEngine,
)
from aistack.transport.delivery_verifier import (
    DeliveryVerifier,
)
from aistack.transport.filesystem import (
    FilesystemReceiver,
    FilesystemWriter,
)
from aistack.transport.registry import (
    InMemoryTransportRegistry,
)


class DummyVerifier(DeliveryVerifier):
    def verify(
        self,
        capability,
        request: TransportRequest,
        result: TransportResult,
    ) -> bool:
        return True


def build_engine(
    repository: FilesystemLocationRepository,
) -> DefaultTransportEngine:

    resolver = FilesystemLocationResolver(repository)

    capability = FilesystemTransportCapability(
        receiver=FilesystemReceiver(resolver),
        writer=FilesystemWriter(resolver),
    )

    registry = InMemoryTransportRegistry()
    registry.register(
        "filesystem",
        capability,
    )

    return DefaultTransportEngine(
        registry,
        DummyVerifier(),
    )


def build_endpoint() -> TransportEndpoint:

    return TransportEndpoint(
        endpoint_id="local",
        endpoint_type="filesystem",
        uri="unused",
        metadata={},
    )


def test_transport_engine(tmp_path: Path):

    root = tmp_path / "storage"
    root.mkdir()

    hello = root / "hello.txt"
    hello.write_text("Hello AIStack!")

    copy = root / "copy.txt"

    repository = FilesystemLocationRepository(
        {
            "hello.txt": hello,
            "copy.txt": copy,
        }
    )

    engine = build_engine(repository)

    endpoint = build_endpoint()

    result = engine.transport(
        TransportRequest(
            source_resource=ResourceReference(
                resource_type="file",
                resource_id="hello.txt",
            ),
            destination_resource=ResourceReference(
                resource_type="file",
                resource_id="copy.txt",
            ),
            source=endpoint,
            destination=endpoint,
            delivery_mode=DeliveryMode.REPLACE,
            correlation_id="tx1",
        )
    )

    assert copy.read_text() == "Hello AIStack!"
    assert result.delivered is True
    assert result.verified is True
    assert result.status is TransportStatus.VERIFIED


def test_transport_create_when_destination_missing(tmp_path: Path):

    root = tmp_path / "storage"
    root.mkdir()

    hello = root / "hello.txt"
    hello.write_text("Hello AIStack!")

    copy = root / "copy.txt"

    repository = FilesystemLocationRepository(
        {
            "hello.txt": hello,
            "copy.txt": copy,
        }
    )

    engine = build_engine(repository)

    endpoint = build_endpoint()

    result = engine.transport(
        TransportRequest(
            source_resource=ResourceReference(
                resource_type="file",
                resource_id="hello.txt",
            ),
            destination_resource=ResourceReference(
                resource_type="file",
                resource_id="copy.txt",
            ),
            source=endpoint,
            destination=endpoint,
            delivery_mode=DeliveryMode.CREATE,
            correlation_id="tx-create",
        )
    )

    assert copy.exists()
    assert copy.read_text() == "Hello AIStack!"
    assert result.status is TransportStatus.VERIFIED


def test_transport_create_when_destination_exists(tmp_path: Path):

    root = tmp_path / "storage"
    root.mkdir()

    hello = root / "hello.txt"
    hello.write_text("Hello AIStack!")

    copy = root / "copy.txt"
    copy.write_text("Already here")

    repository = FilesystemLocationRepository(
        {
            "hello.txt": hello,
            "copy.txt": copy,
        }
    )

    engine = build_engine(repository)

    endpoint = build_endpoint()

    result = engine.transport(
        TransportRequest(
            source_resource=ResourceReference(
                resource_type="file",
                resource_id="hello.txt",
            ),
            destination_resource=ResourceReference(
                resource_type="file",
                resource_id="copy.txt",
            ),
            source=endpoint,
            destination=endpoint,
            delivery_mode=DeliveryMode.CREATE,
            correlation_id="tx-create-fail",
        )
    )

    assert result.status is TransportStatus.FAILED
    assert result.delivered is False
    assert result.verified is False
    assert copy.read_text() == "Already here"
