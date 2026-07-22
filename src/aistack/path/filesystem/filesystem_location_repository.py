"""
Filesystem implementation of the Location Repository.
"""

from __future__ import annotations

from pathlib import Path

from aistack.location.interfaces.location_repository import LocationRepository
from aistack.transport.contracts.resource_reference import ResourceReference


class FilesystemLocationRepository(LocationRepository):
    """
    Resolves physical locations for governed resources.
    """

    def __init__(self, mappings: dict[str, Path]):
        self._mappings = mappings

    def locate(
        self,
        resource: ResourceReference,
    ) -> Path:
        """
        Locate a governed resource through the LocationRepository contract.
        """
        return self._mappings[resource.resource_id]
