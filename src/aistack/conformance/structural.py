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

**`isinstance` cannot answer.** These Protocols are not
`runtime_checkable`, and making them so would compare method
names without looking at call shapes — a class with a `get` that
takes different parameters would pass. So the comparison is
structural and explicit.

Nothing here decides what a violation *means*. `STD-P-002` makes
a contract written ahead of its implementation the prescribed
order, not a defect, so a contract that nothing satisfies is a
fact to publish and not a fault to raise. This module reports;
the qualification belongs to the owner.
"""

from __future__ import annotations

import inspect

from typing import Protocol, TypeVar


_T = TypeVar("_T")


class _EmptyProtocol(Protocol):
    pass


class _EmptyGenericProtocol(Protocol[_T]):
    pass


# Everything a Protocol carries before anyone declares anything
# in it: `__module__`, `_is_protocol`, `__parameters__` and the
# rest. Measured from two empty Protocols rather than listed by
# hand, because that list changes between Python versions and a
# hardcoded one would rot silently.
#
# Subtracting a measured set instead of filtering on a leading
# underscore is what lets `__contains__` be part of a contract.
# It is a real member with a real call shape; a check that
# skipped it would declare a registry conformant without ever
# looking at how membership is tested.
PROTOCOL_NOISE = (
    set(vars(_EmptyProtocol))
    | set(vars(_EmptyGenericProtocol))
    | set(vars(Protocol))
    | set(vars(object))
)


IGNORED_BASES = {"Protocol", "Generic", "object", "ABC"}


class _Unset:
    """A member the contract names without giving it a value."""


_UNSET = _Unset()


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
