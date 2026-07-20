"""
Knowledge Transport Layer - Delivery modes.
"""

from enum import Enum


class DeliveryMode(str, Enum):
    """Governed delivery behavior."""

    CREATE = "create"
    REPLACE = "replace"
