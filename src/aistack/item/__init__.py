"""Governed Item domain.

Everything AIStack manages is a Governed Item.
"""

from .interfaces import GovernedItem
from .lifecycle import ItemLifecycle, ItemLifecycleStatus
from .metadata import ItemMetadata
from .models import Item
from .registry import (
    ItemAlreadyRegisteredError,
    ItemNotFoundError,
    ItemRegistry,
)

__all__ = [
    "GovernedItem",
    "Item",
    "ItemAlreadyRegisteredError",
    "ItemLifecycle",
    "ItemLifecycleStatus",
    "ItemMetadata",
    "ItemNotFoundError",
    "ItemRegistry",
]


# OPS-0012: in quarantine until 2026-11-16 — any use of this module is recorded.
from aistack.quarantine.tripwire import tripwire

tripwire(__name__)
