"""
`aistack.conformance.inventory.take_inventory()`, measured against
the two Protocols this package declares — pinning the resolution of
`GOV-0002/OS-059` rather than letting the fix drift unnoticed.

`Collector[T]` and `Normalizer[TIn, TOut]`
(`kernel/evidence/collector.py`, `kernel/evidence/normalizer.py`)
are proven conformant by `mypy src`, not by this measurement — both
Protocol docstrings say so. This file used to pin the automated
tool's own, then-wrong, opinion of `Normalizer`: satisfied by nearly
the whole package, because `aistack.conformance.structural` read
`__call__` through a live `getattr`, which never fails — a class
that defines no `__call__` of its own is answered by the metaclass's
`type.__call__` instead, exposed as the fully generic
`(*args, **kwargs)`, which happened to match `Normalizer`'s own
two-parameter shape (`self`, `raw`) in length.

**Resolved 2026-09-18** — `_own_member` (`aistack.conformance
.structural`) now reads a name from the implementation's own
`__mro__`, exactly as `protocol_members` already did on the protocol
side, rather than through `getattr`/`hasattr`. `Normalizer` is now
correctly read as an orphan too, the same honest, unimplemented-by-
any-class reading `Collector` already had.
"""

from __future__ import annotations

from aistack.conformance.inventory import take_inventory


def _contract(name: str):
    inventory = take_inventory()

    return next(c for c in inventory.contracts if c.name == name)


def test_collector_is_correctly_read_as_an_orphan():
    assert _contract("Collector").is_orphan


def test_normalizer_is_now_correctly_read_as_an_orphan_too():
    """
    Before the `OS-059` fix, this contract was read as satisfied by
    over 100 classes, none of which had ever declared a `__call__`.
    `mypy src` is what actually proves `Normalizer` conformant
    (its own docstring says so) — this measurement only had to stop
    lying about it.
    """

    normalizer = _contract("Normalizer")

    assert normalizer.is_orphan
    assert normalizer.satisfied_by == ()
