from __future__ import annotations

from aistack.kernel.contracts import KnowledgeProvider
from aistack.kernel.registry import Registry


class ProviderRegistry(Registry[KnowledgeProvider]):
    """Registry of Knowledge Providers."""

    pass
