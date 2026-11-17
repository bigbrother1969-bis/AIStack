from pathlib import Path

from aistack.context_bundle.export.readme_bundle_exporter import (
    ReadmeBundleExporter,
)


def test_readme_bundle_exporter():

    expected = (
        Path(__file__)
        .resolve()
        .parents[4]
        / "README.md"
    ).read_text(
        encoding="utf-8",
    )

    exporter = ReadmeBundleExporter()

    assert exporter.export() == expected
