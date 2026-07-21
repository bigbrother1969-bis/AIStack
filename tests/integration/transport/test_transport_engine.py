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

    repository = FilesystemPathRepository(
        {
            "hello.txt": hello_file,
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

    resource = ResourceReference(
        resource_type="file",
        resource_id="hello.txt",
    )

    request = TransportRequest(
        resource=resource,
        source=endpoint,
        destination=endpoint,
        delivery_mode=DeliveryMode.REPLACE,
        correlation_id="tx1",
    )

    result = engine.transport(request)

    assert hello_file.read_text() == "Hello AIStack!"
    assert result.delivered is True
    assert result.verified is True
    assert result.status is TransportStatus.VERIFIED
