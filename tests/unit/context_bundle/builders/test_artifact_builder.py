from pathlib import Path

from aistack.contracts.discovery import DiscoveryResult
from aistack.context_bundle.builders.artifact_builder import (
    MarkdownArtifactBuilder,
)


def test_markdown_artifact_builder():

    discovery = DiscoveryResult(
        path=Path("docs/test.md"),
        content="# Test",
        content_hash="abc123",
    )

    builder = MarkdownArtifactBuilder()

    artifact = builder.build(discovery)

    assert artifact.id == "abc123"
    assert artifact.title == "test"
    assert artifact.source == "docs/test.md"
    assert artifact.domain == "Knowledge Assets"
    assert artifact.semantic_type == "Knowledge Artifact"
