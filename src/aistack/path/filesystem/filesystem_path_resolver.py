"""
Filesystem implementation of the Path Resolver.
"""

from __future__ import annotations

from pathlib import Path

from aistack.path.filesystem.filesystem_path_repository import (
    FilesystemPathRepository,
)
from aistack.path.interfaces.path_resolver import PathResolver
from aistack.transport.contracts.resource_reference import ResourceReference


class FilesystemPathResolver(PathResolver):
    """
    Resolves physical filesystem paths.
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
        return self._repository.get(resource.resource_id)
