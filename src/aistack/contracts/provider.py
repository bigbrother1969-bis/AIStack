from typing import Iterable, Protocol

from aistack.contracts.artifact import KnowledgeArtifact


class KnowledgeProvider(Protocol):
    name: str

    def observe(self) -> Iterable[KnowledgeArtifact]:
        ...
