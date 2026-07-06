from typing import Protocol

from aistack.contracts.artifact import KnowledgeArtifact


class KnowledgePolicy(Protocol):
    name: str

    def validate(self, artifact: KnowledgeArtifact) -> bool:
        ...
