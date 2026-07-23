from __future__ import annotations

from aistack.kernel.contracts.discovery_provider import DiscoveryProvider
from aistack.kernel.registry import Registry


class ProviderRegistry(Registry[DiscoveryProvider]):
    """Registry of Discovery Providers."""

    pass
