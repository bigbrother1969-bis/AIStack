from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.artifact_builder import ArtifactBuilder
from aistack.contracts.discovery import DiscoveryResult


class MarkdownArtifactBuilder(ArtifactBuilder):
    """
    Build KnowledgeArtifact objects from Markdown discoveries.

    This builder creates the minimal governed representation.
    Classification and criticality are assigned later.
    """

    def build(
        self,
        discovery: DiscoveryResult,
    ) -> KnowledgeArtifact:

        now = datetime.now()

        return KnowledgeArtifact(
            id=discovery.content_hash,
            title=discovery.path.stem,
            domain="Knowledge Assets",
            semantic_type="Knowledge Artifact",
            criticality=1,
            owner="AIStack",
            source=str(discovery.path),
            content=discovery.content,
            created_at=now,
            updated_at=now,
            metadata={
                "content_hash": discovery.content_hash,
            },
        )
