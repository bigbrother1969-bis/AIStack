from typing import Protocol

from aistack.contracts.artifact import KnowledgeArtifact


class KnowledgeRenderer(Protocol):
    name: str

    def render(self, artifact: KnowledgeArtifact) -> str:
        ...
