import json

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


def test_json_manifest_serializer_exposes_integrity():

    manifest = DefaultBundleManifest(
        _bundle_id="bundle-test",
        _generated_at="2026-07-24",
        _source_commit="abcdef",
        _artifact_count=5,
        _repository_url="https://example.org/aistack.git",
        _content_hash="b" * 64,
    )

    data = json.loads(
        JsonManifestSerializer().serialize(
            manifest
        )
    )

    assert data["repository_url"] == (
        "https://example.org/aistack.git"
    )

    assert data["content_hash"] == "b" * 64

    assert data["hash_algorithm"] == "sha256"
