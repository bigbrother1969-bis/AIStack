"""
Filesystem implementation of the Location Resolver.
"""

from __future__ import annotations

from pathlib import Path

from aistack.location.filesystem.filesystem_location_repository import (
    FilesystemLocationRepository,
)
from aistack.location.interfaces.location_resolver import LocationResolver
from aistack.transport.contracts.resource_reference import ResourceReference


class FilesystemLocationResolver(LocationResolver):
    """
    Resolves physical filesystem locations.
    """

    def __init__(
        self,
        repository: FilesystemLocationRepository,
    ):
        self._repository = repository

    def resolve(
        self,
        resource: ResourceReference,
    ) -> Path:
        return self._repository.locate(resource)
