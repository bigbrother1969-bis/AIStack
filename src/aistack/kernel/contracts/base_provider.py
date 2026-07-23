from __future__ import annotations

from typing import Protocol


class Provider(Protocol):
    """
    Make information from an external source available to AIStack.

    A Provider defines the generic information-entry concept.
    It does not prescribe how information is obtained.
    """

    provider_id: str
    provider_name: str
