from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class KnowledgeArtifact:
    id: str
    title: str
    type: str
    owner: str
    source: str
    created_at: datetime
    updated_at: datetime
    confidence: str = "unknown"
    status: str = "draft"
    metadata: dict[str, Any] = field(default_factory=dict)
