from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact


@dataclass(frozen=True)
class ContextBundle:
    id: str
    title: str
    generated_at: datetime
    source_commit: str
    artifacts: list[KnowledgeArtifact] = field(default_factory=list)
    output_path: Path | None = None
