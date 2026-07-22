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

    This transitional implementation supports both:

    - the legacy path-oriented ``get(resource_id)`` API;
    - the location-oriented ``locate(resource)`` contract.
    """

    def __init__(self, mappings: dict[str, Path]):
        self._mappings = mappings

    def get(self, resource_id: str) -> Path:
        """
        Return the filesystem location associated with a resource identifier.

        Kept temporarily for compatibility with existing path consumers.
        """
        return self._mappings[resource_id]

    def locate(
        self,
        resource: ResourceReference,
    ) -> Path:
        """
        Locate a governed resource through the LocationRepository contract.
        """
        return self.get(resource.resource_id)
