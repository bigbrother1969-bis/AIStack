from aistack.contracts.bundle_manifest import (
    BundleManifest,
)


class DummyBundleManifest(BundleManifest):

    @property
    def bundle_id(self):
        return "bundle-test"

    @property
    def generated_at(self):
        return "2026-07-24T00:00:00"

    @property
    def source_commit(self):
        return "abcdef"

    @property
    def artifact_count(self):
        return 10

    @property
    def format_version(self):
        return "1.0"


def test_bundle_manifest_contract():

    manifest = DummyBundleManifest()

    assert manifest.bundle_id == "bundle-test"
    assert manifest.source_commit == "abcdef"
    assert manifest.artifact_count == 10
    assert manifest.format_version == "1.0"
