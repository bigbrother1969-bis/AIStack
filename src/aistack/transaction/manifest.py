from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import Transaction
from .transaction_manifest import TransactionManifest


class ManifestBuilder:
    """Build a typed manifest from a Transaction."""

    def build(self, tx: Transaction) -> TransactionManifest:
        return TransactionManifest(
            transaction_id=tx.transaction_id,
            definition_id=tx.definition_id,
            payload=str(tx.payload),
        )

    def as_dict(self, tx: Transaction) -> dict[str, Any]:
        """Return a serializable dictionary representation."""
        return asdict(self.build(tx))
