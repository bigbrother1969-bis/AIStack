from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact


class RepositoryProvider:
    name = "repository-provider"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def observe(self) -> Iterable[KnowledgeArtifact]:
        readme = self.root / "README.md"

        if not readme.exists():
            return []

        return [self._build_artifact(readme)]

    def _build_artifact(self, path: Path) -> KnowledgeArtifact:
        stat = path.stat()
        relative_path = path.relative_to(self.root)

        timestamp = datetime.fromtimestamp(stat.st_mtime)

        return KnowledgeArtifact(
            id=str(relative_path),
            title=path.stem,
            type="documentation",
            owner=self.name,
            source=str(relative_path),
            created_at=timestamp,
            updated_at=timestamp,
            confidence="high",
            status="observed",
            metadata={
                "path": str(relative_path),
                "size_bytes": stat.st_size,
                "extension": path.suffix,
            },
        )
