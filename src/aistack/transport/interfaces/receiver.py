from __future__ import annotations

from typing import BinaryIO, Protocol

from aistack.transport.contracts.resource_reference import ResourceReference


class Receiver(Protocol):
    """
    Opens a governed resource for streaming.
    """

    def open(
        self,
        resource: ResourceReference,
    ) -> BinaryIO:
        ...
