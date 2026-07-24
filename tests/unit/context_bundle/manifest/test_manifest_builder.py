from aistack.context_bundle.manifest.manifest_builder import (
    DefaultBundleManifest,
)


def test_manifest_builder():

    manifest = DefaultBundleManifest(
        _bundle_id="bundle-test",
        _generated_at="2026-07-24",
        _source_commit="abcdef",
        _artifact_count=5,
    )

    assert manifest.bundle_id == "bundle-test"

    assert manifest.source_commit == "abcdef"

    assert manifest.artifact_count == 5

    assert manifest.format_version == "1.0"
