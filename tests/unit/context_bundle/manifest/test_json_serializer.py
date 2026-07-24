from aistack.context_bundle.manifest.json_serializer import (
    JsonManifestSerializer,
)

from aistack.context_bundle.manifest.manifest_builder import (
    DefaultBundleManifest,
)


def test_json_manifest_serializer():

    manifest = DefaultBundleManifest(
        _bundle_id="bundle-test",
        _generated_at="2026-07-24",
        _source_commit="abcdef",
        _artifact_count=5,
    )

    serializer = JsonManifestSerializer()

    content = serializer.serialize(
        manifest
    )

    assert "bundle-test" in content

    assert "abcdef" in content

    assert '"artifact_count": 5' in content
