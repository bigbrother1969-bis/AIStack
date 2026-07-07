from __future__ import annotations

from typing import Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    """Generic registry used throughout AIStack."""

    def __init__(self) -> None:
        self._entries: dict[str, T] = {}

    def register(self, identifier: str, entry: T) -> None:
        if identifier in self._entries:
            raise ValueError(f"Registry entry already exists: {identifier}")
        self._entries[identifier] = entry

    def get(self, identifier: str) -> T:
        return self._entries[identifier]

    def all(self) -> dict[str, T]:
        return dict(self._entries)

    def __contains__(self, identifier: str) -> bool:
        return identifier in self._entries
