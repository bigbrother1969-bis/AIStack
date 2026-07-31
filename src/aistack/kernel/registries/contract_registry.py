from __future__ import annotations

from typing import Type

from aistack.kernel.registry import Registry


class ContractRegistry(Registry[Type]):
    """Registry of official Kernel contracts."""

    def register(self, contract: Type) -> None:
        super().register(contract.__name__, contract)

    def get(self, name: str) -> Type:
        return super().get(name)

    def contains(self, name: str) -> bool:
        return name in self
