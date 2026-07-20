from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from aistack.transport.capabilities.transport_capability import (
        TransportCapability,
    )


class TransportRegistry(Protocol):
    """
    Registry of transport capabilities.
    """

    def get(
        self,
        endpoint_type: str,
    ) -> "TransportCapability":
        """
        Return the capability associated with an endpoint type.
        """
        ...
