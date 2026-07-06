from typing import Iterable, Protocol

from aistack.contracts.artifact import KnowledgeArtifact


class KnowledgeEngine(Protocol):
    name: str

    def process(self, artifacts: Iterable[KnowledgeArtifact]) -> Iterable[KnowledgeArtifact]:
        ...
