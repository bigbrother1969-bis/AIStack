from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .models import Transaction


class ManifestBuilder:
    """Build a minimal manifest from a Transaction."""

    def build(self, tx: Transaction) -> dict[str, Any]:
        data = asdict(tx)
        data["payload"] = str(tx.payload)
        return data
