import json
import zipfile

from aistack.context_bundle.service import (
    DefaultContextBundleService,
)


def test_manifest_is_in_context_bundle_zip(tmp_path):

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


    service.generate(
        source,
        output,
        "commit123",
    )


    assert output.exists()


    with zipfile.ZipFile(output) as archive:

        files = archive.namelist()

        assert "manifest.json" in files


        content = archive.read(
            "manifest.json"
        ).decode(
            "utf-8"
        )


        manifest = json.loads(
            content
        )


        assert manifest["source_commit"] == "commit123"

        assert manifest["format_version"] == "1.0"
