from __future__ import annotations

from typing import Protocol, TypeVar

from aistack.kernel.contracts.registry import Registry

T = TypeVar("T")


class MutableRegistry(Registry[T], Protocol):
    """
    A Registry that also accepts registrations.

    The read/write split is kept because it is real: resolution
    depends on reading a registry, and bootstrap is the only
    phase that writes to one. A consumer that declares
    `Registry[T]` says it will not register anything, and that
    statement is worth being able to make.

    What was removed on 2026-08-21 is `freeze() -> Registry[T]`.
    It expressed a genuine intention — build a registry, then
    publish it as immutable — and no implementation of it ever
    existed. A contract method nobody wrote is not an intention,
    it is a claim; the intention belongs in an ADR, where it can
    be decided, or in code, where it can be run.

    `register(identifier, entry)` takes both, because a registry
    keyed by identifier cannot derive the key from an arbitrary
    item. The previous contract declared `register(item)`, which
    no caller could have satisfied.
    """

    def register(
        self,
        identifier: str,
        entry: T,
    ) -> None:
        ...
