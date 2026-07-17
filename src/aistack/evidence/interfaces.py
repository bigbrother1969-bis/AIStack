"""Evidence domain interfaces."""

from typing import Protocol, runtime_checkable

from aistack.item import GovernedItem


@runtime_checkable
class EvidenceItem(GovernedItem, Protocol):
    """A Governed Item representing immutable acquired evidence."""

    @property
    def source(self) -> str:
        """Originating acquisition source."""
