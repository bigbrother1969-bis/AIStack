from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.knowledge_registry import (
    KnowledgeRegistry,
)
from aistack.context_bundle.generation.context_bundle_builder import (
    DefaultContextBundleBuilder,
)


def test_context_bundle_builder_creates_bundle():

    artifact = KnowledgeArtifact(
        id="TEST-001",
        title="Test Artifact",
        domain="Foundation",
        semantic_type="Principle",
        criticality=3,
        owner="AIStack",
        source="test.md",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    registry = KnowledgeRegistry()

    registry.add(artifact)

    builder = DefaultContextBundleBuilder()

    bundle = builder.build(
        registry,
        source_commit="abcdef",
    )

    assert bundle.source_commit == "abcdef"
    assert bundle.title == "AIStack Context Bundle"
    assert len(bundle.artifacts) == 1
    assert bundle.artifacts[0].id == "TEST-001"
