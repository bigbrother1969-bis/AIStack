from pathlib import Path

from aistack.contracts.discovery import DiscoveryResult
from aistack.context_bundle.builders.artifact_builder import (
    MarkdownArtifactBuilder,
)
from aistack.context_bundle.registry.registry_builder import (
    DefaultRegistryBuilder,
)


def test_registry_builder_creates_registry():

    discovery = DiscoveryResult(
        path=Path("docs/test.md"),
        content=(
            "---\nartifact:\n  id: FDN-0003\n"
            "  title: Constitution\n---\n\n# Test\n"
        ),
        content_hash="abc123",
    )

    builder = DefaultRegistryBuilder(
        MarkdownArtifactBuilder()
    )

    registry = builder.build(
        [discovery]
    )

    assert registry.count() == 1

    # The registry is keyed by the governed identifier since
    # 2026-08-23. Before that it was keyed by content hash, so
    # asking it for `FDN-0003` — the only name anyone actually
    # cites — returned nothing, and every consumer had to know a
    # SHA-256 to find a document (GOV-0002/OS-021).
    assert registry.get("abc123") is None

    artifact = registry.get("FDN-0003")

    assert artifact is not None
    assert artifact.title == "Constitution"
    assert artifact.metadata["content_hash"] == "abc123"
