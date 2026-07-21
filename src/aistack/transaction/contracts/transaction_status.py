"""
Knowledge Transaction Manager - Transaction Status.
"""

from __future__ import annotations

from enum import Enum


class TransactionStatus(str, Enum):
    """
    Lifecycle of a governed transaction.
    """

    CREATED = "created"

    RUNNING = "running"

    SUCCEEDED = "succeeded"

    FAILED = "failed"

    ROLLED_BACK = "rolled_back"

    CANCELLED = "cancelled"
