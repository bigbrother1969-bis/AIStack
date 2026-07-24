from pathlib import Path

from aistack.context_bundle.discovery.markdown_discovery import (
    MarkdownDiscovery,
)

from aistack.context_bundle.builders.artifact_builder import (
    MarkdownArtifactBuilder,
)

from aistack.context_bundle.registry.registry_builder import (
    DefaultRegistryBuilder,
)

from aistack.context_bundle.generation.context_bundle_builder import (
    DefaultContextBundleBuilder,
)

from aistack.context_bundle.export.bundle_exporter import (
    JsonBundleExporter,
)


def test_complete_context_bundle_pipeline(tmp_path):

    # Create source knowledge artifact
    source = tmp_path / "example.md"

    source.write_text(
        "# Example Knowledge\n",
        encoding="utf-8",
    )


    # Discovery
    discovery = MarkdownDiscovery()

    discoveries = discovery.discover(
        tmp_path
    )

    assert len(discoveries) == 1


    # Artifact building
    artifact_builder = MarkdownArtifactBuilder()


    # Registry building
    registry_builder = DefaultRegistryBuilder(
        artifact_builder
    )

    registry = registry_builder.build(
        discoveries
    )

    assert registry.count() == 1


    # Context Bundle building
    bundle_builder = DefaultContextBundleBuilder()

    bundle = bundle_builder.build(
        registry,
        source_commit="test123",
    )

    assert len(bundle.artifacts) == 1


    # Export
    output = tmp_path / "bundle.json"

    exporter = JsonBundleExporter()

    exported = exporter.export(
        bundle,
        output,
    )

    assert exported.exists()

    content = exported.read_text(
        encoding="utf-8"
    )

    assert "Example Knowledge" in content
