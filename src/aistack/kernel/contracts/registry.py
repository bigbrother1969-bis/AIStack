from __future__ import annotations

from typing import Protocol, TypeVar

T = TypeVar("T")


class Registry(Protocol[T]):
    """
    Provide governed read-only access to governed Items.

    Until 2026-08-21 this contract required `get`, `contains` and
    `items`. `aistack.kernel.registry.Registry` — the class every
    kernel registry actually derives from — provides `get`, `all`
    and `__contains__`, and never provided the other two. The
    contract described a registry nobody had written.

    Nothing detected it, because the tests of this package
    asserted that the Protocol declared its own methods
    (`callable(Registry.get)`), which a Protocol always does.
    FDN-0011 calls this an orphan contract; the decision recorded
    on 2026-08-21 was to align the contract on what exists, since
    the implementation is the part that ships.

    `__contains__` rather than `contains`: membership is tested
    with `in` in Python, and a contract that renamed it would be
    describing a different language.
    """

    def get(
        self,
        identifier: str,
    ) -> T:
        ...

    def all(
        self,
    ) -> dict[str, T]:
        ...

    def __contains__(
        self,
        identifier: str,
    ) -> bool:
        ...
