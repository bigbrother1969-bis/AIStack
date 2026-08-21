from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle

from aistack.context_bundle.export.markdown_bundle_exporter import (
    MarkdownBundleExporter,
)


def test_markdown_bundle_exporter(tmp_path):

    artifact = KnowledgeArtifact(
        id="TEST-001",
        title="Test Principle",
        declared_type="Test Artifact",
        domain="Foundation",
        semantic_type="Principle",
        criticality="C3",
        owner="AIStack",
        source="test.md",
        status="Proposed",
        content="# My knowledge",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    bundle = ContextBundle(
        id="bundle-test",
        title="Test Bundle",
        generated_at=datetime.now(),
        source_commit="abc123",
        artifacts=[artifact],
    )

    output = tmp_path / "bundle.md"

    exporter = MarkdownBundleExporter()

    result = exporter.export(
        bundle,
        output,
    )

    assert result.exists()

    content = result.read_text(
        encoding="utf-8"
    )

    assert "Test Principle" in content
    assert "# My knowledge" in content
    assert "- Criticality: C3" in content
    assert "- Status: Proposed" in content
    assert "- Confidence: unknown" in content
    assert "- Owner: AIStack" in content
