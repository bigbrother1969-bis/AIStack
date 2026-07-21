"""
Filesystem implementation of the Knowledge Transport Layer Writer.
"""

from __future__ import annotations

from aistack.path.interfaces.path_resolver import PathResolver
from aistack.transport.contracts.resource_reference import ResourceReference


class FilesystemWriter:
    """
    Writes governed resources to the local filesystem.
    """

    def __init__(self, path_resolver: PathResolver):
        self._path_resolver = path_resolver

    def exists(
        self,
        resource: ResourceReference,
    ) -> bool:
        """
        Return True if the destination already exists.
        """
        path = self._path_resolver.resolve(resource)
        return path.exists()

    def write(
        self,
        resource: ResourceReference,
        data: bytes,
    ) -> None:
        """
        Persist the serialized representation of a governed resource.
        """
        path = self._path_resolver.resolve(resource)

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        path.write_bytes(data)
