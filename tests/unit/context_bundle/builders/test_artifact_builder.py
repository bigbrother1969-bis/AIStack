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
  semantic_type: Policy
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
    assert artifact.criticality == "C3"


def test_type_and_semantic_type_are_two_fields():
    """
    STD-0100 v2.0 separates the free label an artifact gives
    itself from the closed vocabulary the pipeline reasons over.

    Until that revision the builder read `type` and stored it
    *as* the semantic type, which is how fourteen free-text
    labels came to travel through the projection as though they
    belonged to a governed vocabulary. This test exists so the
    collapse cannot silently return.
    """

    discovery = DiscoveryResult(
        path=Path("docs/00-foundation/FDN-0009.md"),
        content=DECLARED,
        content_hash="def456",
    )

    artifact = MarkdownArtifactBuilder().build(discovery)

    assert artifact.declared_type == "Foundation Protocol"
    assert artifact.semantic_type == "Policy"


def test_semantic_type_outside_the_vocabulary_is_undeclared():
    """
    A closed vocabulary that accepts anything is not a
    vocabulary. An out-of-vocabulary value is reported as
    undeclared rather than mapped to the nearest plausible term
    — the invalid declaration stays visible in the frontmatter,
    where the validator can report it.
    """

    content = DECLARED.replace(
        "  semantic_type: Policy\n",
        "  semantic_type: Foundation Protocol\n",
    )

    discovery = DiscoveryResult(
        path=Path("docs/00-foundation/FDN-0009.md"),
        content=content,
        content_hash="def456",
    )

    artifact = MarkdownArtifactBuilder().build(discovery)

    assert artifact.semantic_type == "unknown"
    assert artifact.declared_type == "Foundation Protocol"


def test_builder_reports_undeclared_state_as_unknown():
    """
    46 of 84 artifacts declare no metadata at all. Their state
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
    assert artifact.declared_type == "unknown"
