from datetime import datetime

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.artifact_builder import ArtifactBuilder
from aistack.contracts.classification import (
    normalize_domain,
    normalize_semantic_type,
)
from aistack.contracts.criticality import normalize_criticality
from aistack.contracts.discovery import DiscoveryResult

from aistack.context_bundle.builders.frontmatter import (
    declared_value,
    parse_artifact_frontmatter,
)


class MarkdownArtifactBuilder(ArtifactBuilder):
    """
    Build KnowledgeArtifact objects from Markdown discoveries.

    Every governed attribute is taken from what the artifact
    declares about itself. Nothing is inferred.

    This applies to the three qualifications — domain,
    semantic type and criticality — as much as to ownership
    and lifecycle. FDN-0003 Article 4 makes qualification a
    human contribution that the machine assists but never
    replaces; a builder that assigned them would be
    qualifying knowledge on the human's behalf.

    The title is read from the artifact too. Until 2026-08-21
    the builder used `discovery.path.stem`, so the Constitution
    travelled as "FDN-0003-Constitution" while declaring
    `title: Constitution`, and eighteen artifacts appeared to
    share three titles — "README", "architecture",
    "specification" — because those are filenames, not titles.

    `type` and `semantic_type` are read as the two distinct
    fields STD-0100 v2.0 defines. Until that revision the
    builder read `type` and stored it *as* the semantic type,
    which is why fourteen free-text labels were travelling
    through the projection as though they belonged to a closed
    vocabulary.

    What an artifact does not declare is reported as
    "unknown", which is a governed state under Article 12.
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
            # The governed identifier the artifact declares —
            # `FDN-0003`, not a hash. Until 2026-08-23 this field
            # held `discovery.content_hash`, so the projection
            # keyed 65 artifacts by SHA-256 and the identifier the
            # whole heritage cites existed nowhere in the model
            # (GOV-0002/OS-021). A check comparing references
            # against it reported 85 dangling references on a
            # heritage that had none.
            #
            # An artifact declaring no `id` is carried as
            # `unknown`, per FDN-0003 Article 12, rather than
            # given a hash that would look like an identity.
            id=declared_value(
                declared,
                "id",
            ),
            title=declared_value(
                declared,
                "title",
            ),
            domain=normalize_domain(
                declared.get("domain")
            ),
            semantic_type=normalize_semantic_type(
                declared.get("semantic_type")
            ),
            criticality=normalize_criticality(
                declared.get("criticality")
            ),
            declared_type=declared_value(
                declared,
                "type",
            ),
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
