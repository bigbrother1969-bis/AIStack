import json

from aistack.contracts.bundle_manifest import (
    BundleManifest,
)

from aistack.contracts.manifest_serializer import (
    ManifestSerializer,
)


class JsonManifestSerializer(
    ManifestSerializer
):
    """
    JSON serializer for Context Bundle manifests.
    """

    def serialize(
        self,
        manifest: BundleManifest,
    ) -> str:

        return json.dumps(
            {
                "bundle_id": manifest.bundle_id,
                "generated_at": manifest.generated_at,
                "source_commit": manifest.source_commit,
                "repository_url": manifest.repository_url,
                "artifact_count": manifest.artifact_count,
                "content_hash": manifest.content_hash,
                "hash_algorithm": manifest.hash_algorithm,
                "format_version": manifest.format_version,
            },
            indent=2,
        )
