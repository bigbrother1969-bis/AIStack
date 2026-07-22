"""
Filesystem implementation of the Knowledge Transport Layer Receiver.
"""

from __future__ import annotations

from typing import BinaryIO

from aistack.location.interfaces.location_resolver import LocationResolver
from aistack.transport.contracts.resource_reference import ResourceReference


class FilesystemReceiver:
    """
    Opens governed resources from the local filesystem.

    Physical resource locations are provided by a LocationResolver.
    """

    def __init__(self, location_resolver: LocationResolver):
        self._location_resolver = location_resolver

    def open(
        self,
        resource: ResourceReference,
    ) -> BinaryIO:
        location = self._location_resolver.resolve(resource)
        return location.open("rb")
