from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping


@dataclass(frozen=True)
class ExecutionContext:
    execution_id: str
    execution_name: str
    started_at: datetime

    scenario: str | None = None

    tags: Mapping[str, str] = field(default_factory=dict)
    metadata: Mapping[str, Any] = field(default_factory=dict)
