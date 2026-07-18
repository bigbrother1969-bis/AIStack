from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Transaction:
    """Immutable transaction descriptor."""

    transaction_id: str
    definition_id: str
    payload: Path
