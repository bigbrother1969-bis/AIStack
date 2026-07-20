"""
Knowledge Transport Layer - Transport transaction lifecycle.
"""

from enum import Enum


class TransportStatus(str, Enum):
    """Lifecycle of a transport transaction."""

    PENDING = "pending"

    VALIDATED = "validated"

    IN_PROGRESS = "in_progress"

    DELIVERED = "delivered"

    VERIFIED = "verified"

    FAILED = "failed"

    ROLLED_BACK = "rolled_back"

    REDELIVERED = "redelivered"
