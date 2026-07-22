from pathlib import Path

from aistack.path.filesystem.filesystem_location_repository import (
    FilesystemLocationRepository,
)
from aistack.path.filesystem.filesystem_location_resolver import (
    FilesystemLocationResolver,
)
from aistack.transaction.adapters.transport_operation_engine import (
    TransportOperationEngine,
)
from aistack.transaction.contracts.operation import Operation
from aistack.transaction.contracts.transaction import Transaction
from aistack.transaction.executor.default_transaction_executor import (
    DefaultTransactionExecutor,
)
from aistack.transaction.registry.in_memory_operation_registry import (
    InMemoryOperationRegistry,
)
from aistack.transport.capabilities.filesystem_transport_capability import (
    FilesystemTransportCapability,
)
from aistack.transport.contracts import (
    DeliveryMode,
    ResourceReference,
    TransportEndpoint,
    TransportRequest,
    TransportResult,
)
from aistack.transport.default_transport_engine import (
    DefaultTransportEngine,
)
from aistack.transport.delivery_verifier import (
    DeliveryVerifier,
)
from aistack.transport.filesystem.filesystem_receiver import (
    FilesystemReceiver,
)
from aistack.transport.filesystem.filesystem_writer import (
    FilesystemWriter,
)
from aistack.transport.registry.in_memory_transport_registry import (
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


def test_transport_transaction(tmp_path: Path):

    root = tmp_path / "storage"
    root.mkdir()

    source = root / "hello.txt"
    destination = root / "copy.txt"

    source.write_text("Hello AIStack!")

    repository = FilesystemLocationRepository(
        {
            "hello.txt": source,
            "copy.txt": destination,
        }
    )

    resolver = FilesystemLocationResolver(repository)

    capability = FilesystemTransportCapability(
        receiver=FilesystemReceiver(resolver),
        writer=FilesystemWriter(resolver),
    )

    transport_registry = InMemoryTransportRegistry()
    transport_registry.register(
        "filesystem",
        capability,
    )

    transport_engine = DefaultTransportEngine(
        transport_registry,
        DummyVerifier(),
    )

    operation_registry = InMemoryOperationRegistry()
    operation_registry.register(
        "transport",
        TransportOperationEngine(
            transport_engine,
        ),
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
        source=TransportEndpoint(
            endpoint_id="local",
            endpoint_type="filesystem",
            uri="unused",
        ),
        destination=TransportEndpoint(
            endpoint_id="local",
            endpoint_type="filesystem",
            uri="unused",
        ),
        delivery_mode=DeliveryMode.REPLACE,
    )

    transaction = Transaction(
        operations=[
            Operation(
                name="transport",
                kind="transport",
                payload=request,
            )
        ]
    )

    executor = DefaultTransactionExecutor(
        operation_registry,
    )

    executor.execute(transaction)

    assert destination.exists()
    assert destination.read_text() == "Hello AIStack!"
