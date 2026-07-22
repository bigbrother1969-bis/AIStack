"""
Filesystem implementation of the Location Resolver.
"""

from __future__ import annotations

from pathlib import Path

from aistack.location.interfaces.location_resolver import LocationResolver
from aistack.path.filesystem.filesystem_location_repository import (
    FilesystemLocationRepository,
)
from aistack.path.interfaces.path_resolver import PathResolver
from aistack.transport.contracts.resource_reference import ResourceReference


class FilesystemLocationResolver(PathResolver, LocationResolver):
    """
    Resolves physical filesystem locations.

    During the Path-to-Location transition, this implementation satisfies
    both resolver contracts.
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
