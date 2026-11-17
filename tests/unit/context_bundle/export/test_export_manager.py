from datetime import datetime
import zipfile

from aistack.contracts.artifact import (
    KnowledgeArtifact,
)

from aistack.contracts.context_bundle import (
    ContextBundle,
)

from aistack.context_bundle.export.export_manager import (
    DefaultBundleExportManager,
)


def test_export_manager_creates_complete_bundle(tmp_path):

    artifact = KnowledgeArtifact(
        id="TEST-001",
        title="Test Principle",
        declared_type="Test Artifact",
        domain="Foundation",
        semantic_type="Principle",
        criticality=3,
        owner="AIStack",
        source="test.md",
        content="# Knowledge",
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

    output = tmp_path / "bundle.zip"

    manager = DefaultBundleExportManager()

    result = manager.export(
        bundle,
        output,
    )

    assert result.exists()

    assert (
        tmp_path / "bundle.json"
    ).exists()

    assert (
        tmp_path / "bundle.md"
    ).exists()


    with zipfile.ZipFile(result) as archive:

        assert "bundle.json" in archive.namelist()
        assert "bundle.md" in archive.namelist()
