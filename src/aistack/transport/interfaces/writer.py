"""
Knowledge Transport Layer - Writer interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.resource_reference import ResourceReference


class Writer(Protocol):
    """
    Writes a governed resource to a destination.
    """

    def exists(
        self,
        resource: ResourceReference,
    ) -> bool:
        """
        Return True if the destination resource already exists.
        """
        ...

    def write(
        self,
        resource: ResourceReference,
        data: bytes,
    ) -> None:
        """
        Persist the serialized representation of a resource.
        """
        ...
