"""
Knowledge Transport Layer - Knowledge Artifact contract.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class KnowledgeArtifact:
    """
    Content-agnostic artifact transported by the Knowledge Transport Layer.

    A Knowledge Artifact represents governed knowledge only.
    It never contains any physical location information.
    """

    artifact_id: str

    name: str

    media_type: str

    size_bytes: int

    sha256: str

    metadata: Mapping[str, Any] = field(default_factory=dict)
