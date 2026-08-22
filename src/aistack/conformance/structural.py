"""
Decide whether an implementation satisfies a contract.

FDN-0011 defines technical debt as a property of the contracts —
missing contracts, orphan contracts, orphan implementations,
contracts describing obsolete concepts — and states that the debt
is *derived from violations of the contract architecture rather
than from subjective code reviews*.

Deriving it requires answering one question mechanically: does
anything satisfy this contract? This module answers it, and until
2026-08-22 the only code that could lived in the test tree
(GOV-0002/OS-002), which meant the product could not measure its
own contracts.

**`isinstance` cannot answer.** Most Protocols here are not
`runtime_checkable`, so `isinstance` refuses outright; the two
that are — `GovernedItem` and `EvidenceItem`, as of 2026-08-22 —
would compare member names without looking at call shapes, and a
class whose `get` takes different parameters would pass. So the
comparison is structural and explicit for all of them.

Nothing here decides what a violation *means*. `STD-P-002` makes
a contract written ahead of its implementation the prescribed
order, not a defect, so a contract that nothing satisfies is a
fact to publish and not a fault to raise. This module reports;
the qualification belongs to the owner.
"""

from __future__ import annotations

import inspect

from abc import ABC
from typing import Protocol, TypeVar, runtime_checkable


def _measure_noise() -> frozenset[str]:
    """
    Everything a contract carries before anyone declares anything
    in it.

    Measured from empty contracts of **every form** rather than
    listed by hand: that list changes between Python versions, and
    a hardcoded one would rot in silence.

    All four forms are needed, and the fourth was learned the hard
    way. CPython 3.12 adds `__non_callable_proto_members__` to
    every `runtime_checkable` Protocol. Measuring from bare
    Protocols alone left that name looking like a requirement no
    class satisfies, so the two decorated contracts of this
    heritage — `GovernedItem` and `EvidenceItem` — were reported
    as orphans on 3.12 and 3.13 while being satisfied on 3.11.

    Found 2026-08-22 by running the same commit on two machines:
    20 orphans on one, 22 on the other. A measurement of technical
    debt that answers differently per interpreter is not a
    measurement, and STD-0300 § 6 requires that an unchanged input
    produce an identical output.

    The fixtures are local to this function on purpose. Declared
    at module level they became classes of the package, and the
    inventory counted them among its concrete implementations —
    the instrument appearing in its own measurement for the second
    time in one afternoon.
    """

    _T = TypeVar("_T")

    class _EmptyProtocol(Protocol):
        pass

    class _EmptyGenericProtocol(Protocol[_T]):
        pass

    @runtime_checkable
    class _EmptyRuntimeCheckableProtocol(Protocol):
        pass

    class _EmptyABC(ABC):
        pass

    return frozenset(
        set(vars(_EmptyProtocol))
        | set(vars(_EmptyGenericProtocol))
        | set(vars(_EmptyRuntimeCheckableProtocol))
        | set(vars(_EmptyABC))
        | set(vars(Protocol))
        | set(vars(ABC))
        | set(vars(object))
    )


# Subtracting a measured set instead of filtering on a leading
# underscore is what lets `__contains__` be part of a contract.
# It is a real member with a real call shape; a check that
# skipped it would declare a registry conformant without ever
# looking at how membership is tested.
PROTOCOL_NOISE = _measure_noise()


IGNORED_BASES = {"Protocol", "Generic", "object", "ABC"}


# A sentinel, not a class: a class declared here would be
# inventoried among the package's concrete implementations.
_UNSET = object()


def protocol_members(protocol: type) -> set[str]:
    """
    The names a contract requires, including the ones it inherits.

    Read from the contract's own namespaces rather than from
    `__protocol_attrs__`, which is a CPython internal added in
    3.12 — code that used it would silently require that version.

    The walk over `__mro__` is the whole point. `MutableRegistry`
    extends `Registry`, so it requires four members; reading only
    its own namespace reports one, and a conformance check that
    under-reports what a contract demands is the same failure it
    was written to catch.
    """

    required: set[str] = set()

    for base in protocol.__mro__:

        if base.__name__ in IGNORED_BASES:
            continue

        required.update(vars(base))

        # An annotated attribute is a requirement with no value.
        # `class Provider(Protocol): provider_id: str` puts
        # nothing in `vars()` except the `__annotations__` mapping
        # itself, so reading `vars()` alone reports that this
        # contract requires `__annotations__` and nothing else —
        # which every class in the package satisfies.
        #
        # Measured 2026-08-22: that is exactly what happened.
        # `Provider` was reported as satisfied by all 144 concrete
        # classes. The error under-declares the debt, which is the
        # direction that matters.
        required.update(getattr(base, "__annotations__", {}))

    required -= PROTOCOL_NOISE

    # The mapping is machinery, never a requirement. Its *keys*
    # are the requirements, and they were just added.
    required.discard("__annotations__")

    return required


def missing_members(
    protocol: type,
    implementation: type,
) -> set[str]:
    """Names the contract requires and the implementation lacks."""

    return {
        name
        for name in protocol_members(protocol)
        if not hasattr(implementation, name)
    }


def incompatible_members(
    protocol: type,
    implementation: type,
) -> dict[str, str]:
    """
    Members present on both whose call shape differs.

    Parameter *names* are compared only where the contract makes
    them part of itself. A contract that does not care declares
    the parameter positional-only, which says so in the language
    rather than in a comment.
    """

    problems: dict[str, str] = {}

    for name in protocol_members(protocol) - missing_members(
        protocol, implementation
    ):

        expected = getattr(protocol, name, _UNSET)
        actual = getattr(implementation, name)

        if expected is _UNSET:
            # An annotated attribute: the contract states that the
            # name must exist and gives nothing to compare it to.
            # Presence was already checked by `missing_members`.
            continue

        if not callable(expected):
            continue

        if not callable(actual):
            problems[name] = "declared callable, implemented as a value"
            continue

        try:
            want = inspect.signature(expected)
            have = inspect.signature(actual)
        except (ValueError, TypeError):
            # A builtin or a C-implemented member carries no
            # introspectable signature. Reporting it as
            # incompatible would be an accusation the tool cannot
            # support; skipping it silently would hide a member
            # nobody compared. It is named as unverifiable.
            problems[name] = "call shape not introspectable"
            continue

        if len(want.parameters) != len(have.parameters):
            problems[name] = f"{want} vs {have}"
            continue

        for a, b in zip(
            want.parameters.values(),
            have.parameters.values(),
        ):
            names_matter = (
                a.kind is not inspect.Parameter.POSITIONAL_ONLY
            )

            if names_matter and a.name != b.name:
                problems[name] = (
                    f"parameter name differs: {want} vs {have}"
                )
                break

    return problems


def satisfies(protocol: type, implementation: type) -> bool:
    """
    Whether `implementation` structurally satisfies `protocol`.

    True requires both: every required name present, and every
    common member's call shape compatible. A class carrying the
    right names with the wrong signatures does not satisfy a
    contract, and reporting it as conformant is how an inventory
    comes to overstate what a heritage guarantees.
    """

    if missing_members(protocol, implementation):
        return False

    return not incompatible_members(protocol, implementation)
