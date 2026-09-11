"""
`aistack.conformance.inventory.take_inventory()`, measured against
the two Protocols this package declares — pinning `GOV-0002/OS-059`
rather than letting it drift unnoticed.

`Collector[T]` and `Normalizer[TIn, TOut]`
(`kernel/evidence/collector.py`, `kernel/evidence/normalizer.py`)
are proven conformant by `mypy src`, not by this measurement — both
Protocol docstrings say so. What is pinned here is the automated
tool's own, currently wrong, opinion of them: `Collector` correctly
read as an orphan, `Normalizer` incorrectly read as satisfied by
nearly the whole package. A fix to `aistack.conformance.structural`
(`OS-059`'s own qualification) should turn the second assertion
below false — which is the point of writing it down rather than
leaving the discovery in a register entry no suite reads.
"""

from __future__ import annotations

from aistack.conformance.inventory import take_inventory


def _contract(name: str):
    inventory = take_inventory()

    return next(c for c in inventory.contracts if c.name == name)


def test_collector_is_correctly_read_as_an_orphan():
    assert _contract("Collector").is_orphan


def test_normalizer_is_incorrectly_read_as_satisfied_by_nearly_everything():
    """
    `GOV-0002/OS-059`: a `__call__`-only Protocol taking one argument
    collides with `type.__call__`'s `(*args, **kwargs)` shape on
    every class that defines no `__call__` of its own. The exact
    count drifts with the package; what must not drift silently is
    the false conclusion — `is_orphan` reading `False` for a
    contract nothing was written to satisfy.
    """

    normalizer = _contract("Normalizer")

    assert not normalizer.is_orphan
    assert len(normalizer.satisfied_by) > 100
