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
        content="# Test",
        content_hash="abc123",
    )

    builder = DefaultRegistryBuilder(
        MarkdownArtifactBuilder()
    )

    registry = builder.build(
        [discovery]
    )

    assert registry.count() == 1

    artifact = registry.get("abc123")

    assert artifact is not None
    assert artifact.title == "test"
