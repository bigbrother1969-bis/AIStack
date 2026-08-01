from __future__ import annotations

from typing import Protocol, TypeVar

from aistack.kernel.contracts.registry import Registry

T = TypeVar("T")


class MutableRegistry(Registry[T], Protocol):
    """
    Build a governed Registry before publishing it as immutable.
    """

    def register(
        self,
        item: T,
    ) -> None:
        ...

    def freeze(
        self,
    ) -> Registry[T]:
        ...
