from collections.abc import Iterable
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact


class RepositoryProvider:
    name = "repository-provider"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def observe(self) -> Iterable[KnowledgeArtifact]:
        return []
