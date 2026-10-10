from __future__ import annotations

from typing import Type

from aistack.kernel.registry import Registry


class ContractRegistry(Registry[Type]):
    """
    Registry of official Kernel contracts.

    `register_contract` derives the identifier from the class name. It
    does not override `register`, whose two-argument signature must stay
    compatible with `Registry`.
    """

    def register_contract(self, contract: Type) -> None:
        self.register(contract.__name__, contract)

    def get(self, name: str) -> Type:
        return super().get(name)

    def contains(self, name: str) -> bool:
        return name in self
