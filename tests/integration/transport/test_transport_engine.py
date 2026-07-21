from pathlib import Path

from aistack.path.filesystem import (
    FilesystemPathRepository,
    FilesystemPathResolver,
)
from aistack.transport import DefaultTransportEngine
from aistack.transport.capabilities import FilesystemTransportCapability
from aistack.transport.contracts import (
    DeliveryMode,
    ResourceReference,
    TransportEndpoint,
    TransportRequest,
    TransportStatus,
)
from aistack.transport.filesystem import (
    FilesystemReceiver,
    FilesystemWriter,
)
from aistack.transport.registry import InMemoryTransportRegistry


class DummyVerifier:
    def verify(self, request, result) -> bool:
        return True


def test_transport_engine(tmp_path: Path):
    root = tmp_path / "storage"
    root.mkdir()

    hello_file = root / "hello.txt"
    hello_file.write_text("Hello AIStack!")

    copy_file = root / "copy.txt"

    repository = FilesystemPathRepository(
        {
            "hello.txt": hello_file,
            "copy.txt": copy_file,
        }
    )

    resolver = FilesystemPathResolver(repository)

    receiver = FilesystemReceiver(resolver)
    writer = FilesystemWriter(resolver)

    capability = FilesystemTransportCapability(
        receiver=receiver,
        writer=writer,
        verifier=DummyVerifier(),
    )

    registry = InMemoryTransportRegistry()
    registry.register("filesystem", capability)

    engine = DefaultTransportEngine(registry)

    endpoint = TransportEndpoint(
        endpoint_id="local",
        endpoint_type="filesystem",
        uri="unused",
        metadata={},
    )

    request = TransportRequest(
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

    result = engine.transport(request)

    assert copy_file.read_text() == "Hello AIStack!"
    assert result.delivered is True
    assert result.verified is True
    assert result.status is TransportStatus.VERIFIED

def test_transport_create_when_destination_missing(tmp_path: Path):
    root = tmp_path / "storage"
    root.mkdir()

    hello_file = root / "hello.txt"
    hello_file.write_text("Hello AIStack!")

    copy_file = root / "copy.txt"

    repository = FilesystemPathRepository(
        {
            "hello.txt": hello_file,
            "copy.txt": copy_file,
        }
    )

    resolver = FilesystemPathResolver(repository)

    capability = FilesystemTransportCapability(
        receiver=FilesystemReceiver(resolver),
        writer=FilesystemWriter(resolver),
        verifier=DummyVerifier(),
    )

    registry = InMemoryTransportRegistry()
    registry.register("filesystem", capability)

    engine = DefaultTransportEngine(registry)

    endpoint = TransportEndpoint(
        endpoint_id="local",
        endpoint_type="filesystem",
        uri="unused",
        metadata={},
    )

    request = TransportRequest(
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

    result = engine.transport(request)

    assert copy_file.exists()
    assert copy_file.read_text() == "Hello AIStack!"
    assert result.status is TransportStatus.VERIFIED

def test_transport_create_when_destination_exists(tmp_path: Path):
    root = tmp_path / "storage"
    root.mkdir()

    hello_file = root / "hello.txt"
    hello_file.write_text("Hello AIStack!")

    copy_file = root / "copy.txt"
    copy_file.write_text("Already here")

    repository = FilesystemPathRepository(
        {
            "hello.txt": hello_file,
            "copy.txt": copy_file,
        }
    )

    resolver = FilesystemPathResolver(repository)

    capability = FilesystemTransportCapability(
        receiver=FilesystemReceiver(resolver),
        writer=FilesystemWriter(resolver),
        verifier=DummyVerifier(),
    )

    registry = InMemoryTransportRegistry()
    registry.register("filesystem", capability)

    engine = DefaultTransportEngine(registry)

    endpoint = TransportEndpoint(
        endpoint_id="local",
        endpoint_type="filesystem",
        uri="unused",
        metadata={},
    )

    request = TransportRequest(
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

    result = engine.transport(request)

    assert result.status is TransportStatus.FAILED
    assert result.delivered is False
    assert result.verified is False

    # destination must remain untouched
    assert copy_file.read_text() == "Already here"
