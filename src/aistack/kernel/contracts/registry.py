from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, TypeVar

T = TypeVar("T")


class Registry(Protocol[T]):
    """
    Provide governed read-only access to governed Items.
    """

    def get(
        self,
        identifier: str,
    ) -> T:
        ...

    def contains(
        self,
        identifier: str,
    ) -> bool:
        ...

    def items(
        self,
    ) -> Iterable[T]:
        ...
