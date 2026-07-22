"""
Filesystem implementation of the Path Resolver.
"""

from __future__ import annotations

from pathlib import Path

from aistack.location.interfaces.location_resolver import LocationResolver
from aistack.path.filesystem.filesystem_path_repository import (
    FilesystemPathRepository,
)
from aistack.path.interfaces.path_resolver import PathResolver
from aistack.transport.contracts.resource_reference import ResourceReference


class FilesystemPathResolver(PathResolver, LocationResolver):
    """
    Resolves physical filesystem paths.

    During the Path-to-Location transition, this implementation satisfies
    both resolver contracts.
    """

    def __init__(
        self,
        repository: FilesystemPathRepository,
    ):
        self._repository = repository

    def resolve(
        self,
        resource: ResourceReference,
    ) -> Path:
        return self._repository.locate(resource)
