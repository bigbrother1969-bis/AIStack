from datetime import datetime
import zipfile

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.context_bundle import ContextBundle

from aistack.context_bundle.export.zip_bundle_exporter import (
    ZipBundleExporter,
)


def test_zip_bundle_exporter(tmp_path):

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


    exporter = ZipBundleExporter()

    result = exporter.export(
        bundle,
        output,
    )


    assert result.exists()


    with zipfile.ZipFile(result) as archive:

        names = archive.namelist()

        assert "bundle.json" in names
        assert "bundle.md" in names

