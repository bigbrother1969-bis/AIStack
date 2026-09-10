from __future__ import annotations

from typing import Type

from aistack.kernel.registry import Registry


class ContractRegistry(Registry[Type]):
    """
    Registry of official Kernel contracts.

    **`register_contract`, not an overridden `register`.** Until
    2026-09-10 this class overrode `Registry.register(identifier,
    entry)` with `register(contract)` — same name, different arity,
    deriving `contract.__name__` as the identifier itself. `mypy`
    found it unprompted, on its first run against this codebase: the
    override is incompatible with its own superclass, so any code
    holding a `Registry[Type]`-typed reference (rather than a
    `ContractRegistry` one) and calling `.register(identifier, entry)`
    polymorphically would fail on this subclass — a call every other
    `Registry[T]` subclass in `aistack.kernel.registries` (providers,
    tasks, catalog views, selection strategies) accepts unchanged.

    Nothing in this repository has ever made that polymorphic call —
    `ContractRegistry` is one of the Kernel Context's four registries
    `knowledge_integrity`'s own `unused-registrations` check already
    names as empty after bootstrap, so the defect was never exercised
    live. The fix keeps the one-argument convenience under its own
    name instead of shadowing the inherited one: `register_contract`
    derives the identifier and delegates to the untouched
    `Registry.register`, which stays available with its original,
    honoured signature.
    """

    def register_contract(self, contract: Type) -> None:
        self.register(contract.__name__, contract)

    def get(self, name: str) -> Type:
        return super().get(name)

    def contains(self, name: str) -> bool:
        return name in self
