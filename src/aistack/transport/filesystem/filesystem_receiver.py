"""
Filesystem implementation of the Knowledge Transport Layer Receiver.
"""

from __future__ import annotations

from aistack.path.interfaces.path_resolver import PathResolver
from aistack.transport.contracts.resource_reference import ResourceReference


class FilesystemReceiver:
    """
    Receives governed resources from the local filesystem.
    """

    def __init__(self, path_resolver: PathResolver):
        self._path_resolver = path_resolver

    def receive(
        self,
        resource: ResourceReference,
    ) -> bytes:
        path = self._path_resolver.resolve(resource)

        return path.read_bytes()
