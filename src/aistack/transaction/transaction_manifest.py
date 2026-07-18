from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TransactionManifest:
    """Immutable typed representation of a transaction manifest."""

    transaction_id: str
    definition_id: str
    payload: str
