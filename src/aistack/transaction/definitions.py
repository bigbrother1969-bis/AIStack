from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TransactionDefinition:
    """Declarative description of a transaction kind."""

    definition_id: str
    version: str = "1.0"
