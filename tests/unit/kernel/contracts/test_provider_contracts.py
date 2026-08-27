from __future__ import annotations

from typing import get_type_hints

from aistack.kernel.contracts import (
    KnowledgeProvider,
    Provider,
)
from aistack.providers.compose.provider import ComposeProvider
from aistack.providers.docker.provider import DockerProvider


def test_provider_defines_generic_provider_identity() -> None:
    annotations = get_type_hints(Provider)

    assert annotations["provider_id"] is str
    assert annotations["provider_name"] is str


def test_knowledge_provider_specializes_provider() -> None:
    assert Provider in KnowledgeProvider.__mro__


def test_knowledge_provider_declares_one_activity() -> None:
    """
    FDN-0002 defines a Knowledge Provider as *responsible for
    discovering observations […] they only collect evidence*. One
    activity, two verbs, and `collect` is the method.

    Until 2026-08-27 this protocol extended a `DiscoveryProvider`
    requiring a second method, `discover()`, described in its own
    docstring as the destination of a Runtime migration for which
    `collect` was the legacy.

    Measured on 2026-08-27: six call sites used `collect`, none
    used `discover`, and `aistack.cli.docker_discover` — the
    command named after the model — called `collect` too. The
    migration was abandoned by the owner. GOV-0002/OS-034.
    """

    assert callable(KnowledgeProvider.collect)

    assert not hasattr(KnowledgeProvider, "discover")


def test_the_two_live_providers_satisfy_it() -> None:
    """
    The point of the narrowing, and the reason it is not merely a
    deletion: `ComposeProvider` and `DockerProvider` were one
    method short of a contract that described them, and the method
    they were short of had no caller anywhere.

    They now satisfy it, and `contract-debt` reports two orphans
    fewer.
    """

    for provider in (ComposeProvider, DockerProvider):
        assert callable(provider.collect)
        assert hasattr(provider, "provider_id")
        assert hasattr(provider, "provider_name")


def test_the_registry_holds_what_the_providers_are() -> None:
    """
    `ProviderRegistry` was typed on `DiscoveryProvider` — the half
    nothing implemented — so its declared element type was
    satisfied by nothing it could ever hold. It is typed on
    `KnowledgeProvider` now, which the two registered providers
    satisfy.
    """

    from aistack.kernel.registries.provider_registry import (
        ProviderRegistry,
    )

    registry = ProviderRegistry()

    registry.register("docker", DockerProvider())
    registry.register("compose", ComposeProvider())

    assert registry.get("docker").provider_id
    assert registry.get("compose").provider_id
