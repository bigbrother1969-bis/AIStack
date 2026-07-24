from aistack.context_bundle.export.readme_bundle_exporter import (
    ReadmeBundleExporter,
)


def test_readme_bundle_exporter():

    exporter = ReadmeBundleExporter()

    content = exporter.export()

    assert "AIStack Context Bundle" in content

    assert "manifest.json" in content

    assert "bundle.json" in content
