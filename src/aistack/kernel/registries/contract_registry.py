from __future__ import annotations

from typing import Type


class ContractRegistry:
    """
    Registry of official Kernel contracts.
    """

    def __init__(self) -> None:
        self._contracts: dict[str, Type] = {}

    def register(
        self,
        contract: Type,
    ) -> None:
        self._contracts[contract.__name__] = contract

    def get(
        self,
        name: str,
    ) -> Type:
        return self._contracts[name]

    def contains(
        self,
        name: str,
    ) -> bool:
        return name in self._contracts

    def all(self) -> tuple[Type, ...]:
        return tuple(self._contracts.values())
