"""
Knowledge Transport Layer - Resource Reference contract.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ResourceReference:
    """
    Immutable governed reference to a resource.

    The reference identifies a governed resource independently of its
    physical location or representation.
    """

    resource_type: str

    resource_id: str
