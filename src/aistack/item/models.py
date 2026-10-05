"""Concrete, technology-neutral Governed Item models."""

from dataclasses import dataclass

from .lifecycle import ItemLifecycle
from .metadata import ItemMetadata


@dataclass(frozen=True, slots=True)
class Item:
    """
    Minimal concrete Governed Item.

    Specialized domains such as Evidence and Observation may extend or
    compose this model without changing its governance contract.
    """

    item_id: str
    item_type: str
    metadata: ItemMetadata
    lifecycle: ItemLifecycle

    def __post_init__(self) -> None:
        if not self.item_id.strip():
            raise ValueError("item_id must not be empty")

        if not self.item_type.strip():
            raise ValueError("item_type must not be empty")


# OPS-0012: in quarantine until 2026-11-16 — any use of this module is recorded.
from aistack.quarantine.tripwire import tripwire

tripwire(__name__)
