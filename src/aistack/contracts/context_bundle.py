from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact


@dataclass(frozen=True)
class ContextBundle:
    """
    Immutable representation of a complete AIStack knowledge context.

    A Context Bundle is a portable representation of the governed knowledge
    heritage.

    Classification and criticality do not filter artifacts.
    They define how AI systems interpret and use knowledge.
    """

    id: str

    title: str

    generated_at: datetime

    source_commit: str

    artifacts: list[KnowledgeArtifact] = field(default_factory=list)

    # Canonical location of the governance SPOT this bundle projects
    repository_url: str = "unknown"

    # Governance model versions used during generation
    classification_version: str = "1.0"
    criticality_version: str = "1.0"

    # Generated output location
    output_path: Path | None = None
