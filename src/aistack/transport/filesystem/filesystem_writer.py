"""
Filesystem implementation of the Knowledge Transport Layer Writer.
"""

from __future__ import annotations

import os
import shutil
from typing import BinaryIO

from aistack.location.interfaces.location_resolver import LocationResolver
from aistack.transport.contracts.resource_reference import ResourceReference

CHUNK_SIZE = 8 * 1024 * 1024


class FilesystemWriter:
    """
    Writes governed resources to the local filesystem.

    Physical resource locations are provided by a LocationResolver.
    """

    def __init__(self, location_resolver: LocationResolver):
        self._location_resolver = location_resolver

    def exists(
        self,
        resource: ResourceReference,
    ) -> bool:
        location = self._location_resolver.resolve(resource)
        return location.exists()

    def write(
        self,
        resource: ResourceReference,
        stream: BinaryIO,
    ) -> None:
        location = self._location_resolver.resolve(resource)

        location.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with location.open("wb") as destination:
            shutil.copyfileobj(
                stream,
                destination,
                length=CHUNK_SIZE,
            )
            destination.flush()
            os.fsync(destination.fileno())
