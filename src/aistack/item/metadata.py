"""Governance metadata shared by all Governed Items."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping


@dataclass(frozen=True, slots=True)
class ItemMetadata:
    """Minimum governance metadata attached to a Governed Item."""

    owner: str
    provenance: str
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime | None = None
    trust_score: float | None = None
    attributes: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.owner.strip():
            raise ValueError("owner must not be empty")

        if not self.provenance.strip():
            raise ValueError("provenance must not be empty")

        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")

        if self.updated_at is not None and self.updated_at.tzinfo is None:
            raise ValueError("updated_at must be timezone-aware")

        if self.updated_at is not None and self.updated_at < self.created_at:
            raise ValueError("updated_at must not precede created_at")

        if self.trust_score is not None and not 0.0 <= self.trust_score <= 1.0:
            raise ValueError("trust_score must be between 0.0 and 1.0")

        object.__setattr__(
            self,
            "attributes",
            MappingProxyType(dict(self.attributes)),
        )
