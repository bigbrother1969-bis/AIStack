from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.artifact_builder import ArtifactBuilder
from aistack.contracts.discovery import DiscoveryResult

from aistack.context_bundle.builders.frontmatter import (
    declared_value,
    parse_artifact_frontmatter,
)


class MarkdownArtifactBuilder(ArtifactBuilder):
    """
    Build KnowledgeArtifact objects from Markdown discoveries.

    Ownership, lifecycle status and confidence are taken from
    what the artifact declares about itself. What it does not
    declare is reported as "unknown" rather than assumed.

    Domain, semantic type and criticality are still assigned
    uniformly here. Classification remains an unimplemented
    pipeline stage.
    """

    def build(
        self,
        discovery: DiscoveryResult,
    ) -> KnowledgeArtifact:

        now = datetime.now()

        declared = parse_artifact_frontmatter(
            discovery.content
        )

        return KnowledgeArtifact(
            id=discovery.content_hash,
            title=discovery.path.stem,
            domain="Knowledge Assets",
            semantic_type="Knowledge Artifact",
            criticality=1,
            owner=declared_value(
                declared,
                "owner",
            ),
            source=str(discovery.path),
            content=discovery.content,
            status=declared_value(
                declared,
                "status",
            ),
            confidence=declared_value(
                declared,
                "confidence",
            ),
            created_at=now,
            updated_at=now,
            metadata={
                "content_hash": discovery.content_hash,
            },
        )
