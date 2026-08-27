from __future__ import annotations

from aistack.kernel.contracts.provider import KnowledgeProvider
from aistack.kernel.registry import Registry


class ProviderRegistry(Registry[KnowledgeProvider]):
    """Registry of Knowledge Providers."""

    pass
