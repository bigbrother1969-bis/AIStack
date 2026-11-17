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

    assert manifest.format_version == "1.2"


def test_manifest_builder_integrity_defaults():
    """
    Absent integrity information must remain visible,
    never silently replaced by a plausible value.
    """

    manifest = DefaultBundleManifest(
        _bundle_id="bundle-test",
        _generated_at="2026-07-24",
        _source_commit="abcdef",
        _artifact_count=5,
    )

    assert manifest.repository_url == "unknown"

    assert manifest.content_hash == ""

    assert manifest.hash_algorithm == "sha256"


def test_manifest_builder_carries_integrity():

    manifest = DefaultBundleManifest(
        _bundle_id="bundle-test",
        _generated_at="2026-07-24",
        _source_commit="abcdef",
        _artifact_count=5,
        _repository_url="https://example.org/aistack.git",
        _content_hash="a" * 64,
    )

    assert manifest.repository_url == (
        "https://example.org/aistack.git"
    )

    assert manifest.content_hash == "a" * 64
