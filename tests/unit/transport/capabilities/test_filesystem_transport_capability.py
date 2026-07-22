from __future__ import annotations

from unittest.mock import Mock

from aistack.transport.capabilities.filesystem_transport_capability import (
    FilesystemTransportCapability,
)


def test_filesystem_transport_capability_exposes_receiver_and_writer() -> None:
    receiver = Mock()
    writer = Mock()

    capability = FilesystemTransportCapability(
        receiver=receiver,
        writer=writer,
    )

    assert capability.receiver is receiver
    assert capability.writer is writer
