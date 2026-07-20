"""
Path Repository - Path Resolver interface.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from aistack.transport.contracts.resource_reference import ResourceReference


class PathResolver(Protocol):
    """
    Resolves the physical location of a governed resource.
    """

    def resolve(
        self,
        resource: ResourceReference,
    ) -> Path:
        """
        Return the physical path of a resource.
        """
        ...
