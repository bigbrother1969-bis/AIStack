"""Internal interfaces of the Governed Item domain."""

from typing import Protocol, runtime_checkable

from .lifecycle import ItemLifecycle
from .metadata import ItemMetadata


@runtime_checkable
class GovernedItem(Protocol):
    """Internal interface implemented by every entity managed by AIStack."""

    @property
    def item_id(self) -> str:
        """Return the stable identity of the item."""

    @property
    def item_type(self) -> str:
        """Return the semantic specialization of the item."""

    @property
    def metadata(self) -> ItemMetadata:
        """Return the governance metadata of the item."""

    @property
    def lifecycle(self) -> ItemLifecycle:
        """Return the current lifecycle state of the item."""
