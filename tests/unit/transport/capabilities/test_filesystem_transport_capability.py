from aistack.transport.capabilities.filesystem_transport_capability import (
    FilesystemTransportCapability,
)
from aistack.transport.registry.in_memory_transport_registry import (
    InMemoryTransportRegistry,
)


class DummyReceiver:
    pass


class DummyWriter:
    pass


class DummyVerifier:
    pass


def test_register_filesystem_capability():

    receiver = DummyReceiver()
    writer = DummyWriter()
    verifier = DummyVerifier()

    capability = FilesystemTransportCapability(
        receiver=receiver,
        writer=writer,
        verifier=verifier,
    )

    registry = InMemoryTransportRegistry()

    registry.register(
        "filesystem",
        capability,
    )

    loaded = registry.get("filesystem")

    assert loaded is capability
    assert loaded.receiver is receiver
    assert loaded.writer is writer
    assert loaded.verifier is verifier
