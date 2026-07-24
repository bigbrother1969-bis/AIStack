from dataclasses import dataclass, field

from aistack.contracts.artifact import KnowledgeArtifact


@dataclass
class KnowledgeRegistry:
    """
    Registry of governed AIStack knowledge artifacts.

    The registry provides a governed view of all discovered knowledge
    artifacts before Context Bundle generation.
    """

    artifacts: list[KnowledgeArtifact] = field(default_factory=list)

    def add(self, artifact: KnowledgeArtifact) -> None:
        """
        Register a knowledge artifact.

        Artifact identifiers must be unique.
        """

        if any(existing.id == artifact.id for existing in self.artifacts):
            raise ValueError(
                f"Knowledge artifact already registered: {artifact.id}"
            )

        self.artifacts.append(artifact)

    def get(self, artifact_id: str) -> KnowledgeArtifact | None:
        """
        Retrieve an artifact by identifier.
        """

        for artifact in self.artifacts:
            if artifact.id == artifact_id:
                return artifact

        return None

    def count(self) -> int:
        """
        Return number of registered artifacts.
        """

        return len(self.artifacts)
