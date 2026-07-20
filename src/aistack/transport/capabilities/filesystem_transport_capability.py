from __future__ import annotations

from aistack.transport.interfaces.delivery_verifier import DeliveryVerifier
from aistack.transport.interfaces.receiver import Receiver
from aistack.transport.interfaces.writer import Writer


class FilesystemTransportCapability:
    """
    Filesystem transport capability.

    Groups together all components required to transport
    resources through the local filesystem.
    """

    def __init__(
        self,
        receiver: Receiver,
        writer: Writer,
        verifier: DeliveryVerifier,
    ) -> None:
        self._receiver = receiver
        self._writer = writer
        self._verifier = verifier

    @property
    def receiver(self) -> Receiver:
        return self._receiver

    @property
    def writer(self) -> Writer:
        return self._writer

    @property
    def verifier(self) -> DeliveryVerifier:
        return self._verifier
