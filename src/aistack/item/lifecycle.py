"""Lifecycle primitives for Governed Items."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class ItemLifecycleStatus(StrEnum):
    """Governed Item lifecycle states."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


@dataclass(frozen=True, slots=True)
class ItemLifecycle:
    """Immutable lifecycle state attached to a Governed Item."""

    status: ItemLifecycleStatus = ItemLifecycleStatus.DRAFT
    effective_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.effective_at.tzinfo is None:
            raise ValueError("effective_at must be timezone-aware")
