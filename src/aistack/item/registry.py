"""In-memory registry for Governed Items."""

from collections.abc import Iterator

from .interfaces import GovernedItem


class ItemAlreadyRegisteredError(ValueError):
    """Raised when an Item identity is already registered."""


class ItemNotFoundError(KeyError):
    """Raised when an Item identity is unknown."""


class ItemRegistry:
    """
    Minimal registry of Governed Items.

    Persistence, history and distributed storage deliberately remain outside
    this first domain implementation.
    """

    def __init__(self) -> None:
        self._items: dict[str, GovernedItem] = {}

    def register(self, item: GovernedItem) -> None:
        """Register an Item without silently replacing existing knowledge."""
        if item.item_id in self._items:
            raise ItemAlreadyRegisteredError(item.item_id)

        self._items[item.item_id] = item

    def get(self, item_id: str) -> GovernedItem:
        """Return a registered Item."""
        try:
            return self._items[item_id]
        except KeyError as exc:
            raise ItemNotFoundError(item_id) from exc

    def contains(self, item_id: str) -> bool:
        """Return whether an Item identity is registered."""
        return item_id in self._items

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[GovernedItem]:
        return iter(self._items.values())
