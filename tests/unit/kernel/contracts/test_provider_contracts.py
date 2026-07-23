from __future__ import annotations

from typing import get_type_hints

from aistack.kernel.contracts import (
    DiscoveryProvider,
    KnowledgeProvider,
    Provider,
)


def test_provider_defines_generic_provider_identity() -> None:
    annotations = get_type_hints(Provider)

    assert annotations["provider_id"] is str
    assert annotations["provider_name"] is str


def test_discovery_provider_specializes_provider() -> None:
    assert Provider in DiscoveryProvider.__mro__


def test_knowledge_provider_specializes_discovery_provider() -> None:
    assert DiscoveryProvider in KnowledgeProvider.__mro__


def test_discovery_provider_exposes_discover_capability() -> None:
    assert callable(DiscoveryProvider.discover)
