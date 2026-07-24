from datetime import datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle
from aistack.context_bundle.export.bundle_exporter import (
    JsonBundleExporter,
)


def test_json_bundle_exporter(tmp_path):

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

    bundle = ContextBundle(
        id="bundle-test",
        title="Test Bundle",
        generated_at=datetime.now(),
        source_commit="abcdef",
        artifacts=[artifact],
    )

    output = tmp_path / "bundle.json"

    exporter = JsonBundleExporter()

    result = exporter.export(
        bundle,
        output,
    )

    assert result.exists()

    content = result.read_text(
        encoding="utf-8"
    )

    assert "TEST-001" in content
    assert "Test Artifact" in content
