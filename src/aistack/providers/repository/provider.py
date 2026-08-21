from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED


class RepositoryProvider:
    """
    Observe a repository and report what is there.

    A provider observes. It does not qualify.

    FDN-0003 Article 4 is explicit: observations do not become
    knowledge automatically, and qualification is the human
    contribution. Everything this provider emits is therefore
    left undeclared — domain, semantic type, criticality,
    status, confidence. What it *did* observe, it states:
    identity, source, and the filesystem facts it read.

    Until 2026-08-21 this provider assigned itself
    `type="documentation"`, `confidence="high"` and
    `status="observed"`. Two of those values did not exist in
    any governed vocabulary, and the third was passed to a
    field the contract does not define — so the call raised
    TypeError and no test exercised it. The code was both dead
    and, had it run, qualifying knowledge on the human's
    behalf.
    """

    name = "repository-provider"

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def resolve(self, relative_path: str | Path) -> Path:
        """Resolve a repository-relative path."""
        return self.root / Path(relative_path)

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
            declared_type=UNDECLARED,
            domain=UNDECLARED,
            semantic_type=UNDECLARED,
            criticality=UNDECLARED,
            owner=self.name,
            source=str(relative_path),
            created_at=timestamp,
            updated_at=timestamp,
            metadata={
                "path": str(relative_path),
                "size_bytes": stat.st_size,
                "extension": path.suffix,
            },
        )
