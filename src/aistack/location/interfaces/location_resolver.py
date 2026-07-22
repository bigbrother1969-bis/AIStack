from __future__ import annotations

from pathlib import Path
from typing import Protocol

from aistack.transport.contracts.resource_reference import ResourceReference


class LocationResolver(Protocol):
    """
    Resolves the physical location of a governed resource.

    Implementations may rely on one or more LocationRepository instances.
    """

    def resolve(
        self,
        resource: ResourceReference,
    ) -> Path:
        ...
