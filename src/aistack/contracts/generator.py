from typing import Iterable, Protocol

from aistack.contracts.artifact import KnowledgeArtifact


class KnowledgeGenerator(Protocol):
    name: str

    def generate(self, artifacts: Iterable[KnowledgeArtifact]) -> KnowledgeArtifact:
        ...
