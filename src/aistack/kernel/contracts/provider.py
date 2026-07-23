from __future__ import annotations

from typing import Any, Protocol

from aistack.kernel.contracts.discovery_provider import DiscoveryProvider


class KnowledgeProvider(DiscoveryProvider, Protocol):
    """
    Backward-compatible discovery provider.

    This protocol remains compatible with the current Runtime.
    The legacy collect() method will be removed once the Runtime
    migrates to the Discovery model.
    """

    def collect(self) -> dict[str, Any]:
        ...
