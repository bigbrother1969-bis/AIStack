"""
Knowledge Transaction - Operation Status.
"""

from __future__ import annotations

from enum import Enum


class OperationStatus(str, Enum):
    """
    Lifecycle of a governed operation.
    """

    CREATED = "created"

    RUNNING = "running"

    SUCCEEDED = "succeeded"

    FAILED = "failed"

    SKIPPED = "skipped"

    CANCELLED = "cancelled"
