"""
Knowledge Transport Layer - Receiver interface.
"""

from __future__ import annotations

from typing import Protocol

from aistack.transport.contracts.resource_reference import ResourceReference


class Receiver(Protocol):
    """
    Receives a governed resource from a source endpoint.
    """

    def receive(self, resource: ResourceReference) -> bytes:
        """
        Retrieve the serialized representation of a resource.
        """
        ...
