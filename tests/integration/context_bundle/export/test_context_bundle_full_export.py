from pathlib import Path
import zipfile

from aistack.context_bundle.service import (
    DefaultContextBundleService,
)


def test_context_bundle_full_export(tmp_path):

    source = tmp_path / "knowledge"

    source.mkdir()

    (source / "principle.md").write_text(
        "# Principle\n",
        encoding="utf-8",
    )


    output = (
        tmp_path
        / "bundle.zip"
    )


    service = DefaultContextBundleService()


    bundle = service.generate(
        source,
        output,
        "commit123",
    )


    assert bundle.source_commit == "commit123"

    assert output.exists()


    with zipfile.ZipFile(output) as archive:

        files = archive.namelist()

        assert "bundle.json" in files
        assert "bundle.md" in files
