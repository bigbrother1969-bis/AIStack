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
    assert artifact.domain == "unknown"
    assert artifact.semantic_type == "unknown"
    assert artifact.criticality == "unknown"


DECLARED = """---
artifact:
  id: FDN-0009
  title: AI Collaboration Protocol
  owner: Foundation
  status: Proposed
  type: Foundation Protocol
  domain: Foundation
  criticality: C3
---

# AI Collaboration Protocol
"""


def test_builder_uses_declared_state():

    discovery = DiscoveryResult(
        path=Path("docs/00-foundation/FDN-0009.md"),
        content=DECLARED,
        content_hash="def456",
    )

    artifact = MarkdownArtifactBuilder().build(discovery)

    assert artifact.status == "Proposed"
    assert artifact.owner == "Foundation"
    assert artifact.domain == "Foundation"
    assert artifact.semantic_type == "Foundation Protocol"
    assert artifact.criticality == "C3"


def test_builder_reports_undeclared_state_as_unknown():
    """
    47 of 81 artifacts declare no metadata at all. Their state
    must read as unknown, not as a fabricated default.
    """

    discovery = DiscoveryResult(
        path=Path("docs/test.md"),
        content="# Test",
        content_hash="abc123",
    )

    artifact = MarkdownArtifactBuilder().build(discovery)

    assert artifact.status == "unknown"
    assert artifact.owner == "unknown"
    assert artifact.confidence == "unknown"
    assert artifact.domain == "unknown"
    assert artifact.semantic_type == "unknown"
    assert artifact.criticality == "unknown"
