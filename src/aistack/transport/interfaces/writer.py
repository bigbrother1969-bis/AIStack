from __future__ import annotations

from typing import BinaryIO, Protocol

from aistack.transport.contracts.resource_reference import ResourceReference


class Writer(Protocol):
    """
    Persists a governed resource from a binary stream.
    """

    def exists(
        self,
        resource: ResourceReference,
    ) -> bool:
        ...

    def write(
        self,
        resource: ResourceReference,
        stream: BinaryIO,
    ) -> None:
        ...
