from __future__ import annotations

from pathlib import Path
from typing import Protocol

from aistack.transport.contracts.resource_reference import ResourceReference


class LocationRepository(Protocol):
    """
    Repository responsible for locating governed resources.

    A LocationRepository abstracts the underlying storage technology
    (filesystem, HTTP, Git, S3, Nextcloud, ...).

    It answers the question:

        "Where is this governed resource located?"
    """

    def locate(
        self,
        resource: ResourceReference,
    ) -> Path:
        ...
