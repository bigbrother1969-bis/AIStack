"""
Filesystem implementation of the Path Repository.
"""

from __future__ import annotations

from pathlib import Path


class FilesystemPathRepository:
    """
    Resolves physical paths for governed resources.

    Temporary implementation.

    A future implementation will use the governed Path Repository.
    """

    def __init__(self, mappings: dict[str, Path]):
        self._mappings = mappings

    def get(self, resource_id: str) -> Path:
        return self._mappings[resource_id]
