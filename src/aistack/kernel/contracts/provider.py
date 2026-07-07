from __future__ import annotations

from typing import Any, Protocol


class KnowledgeProvider(Protocol):
    """Collect governed raw observations from an external source."""

    provider_id: str
    provider_name: str

    def collect(self) -> dict[str, Any]:
        ...
