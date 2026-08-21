"""
Check that an implementation honours a Protocol.

FDN-0011 defines technical debt as a property of the contracts:
missing contracts, orphan contracts, orphan implementations,
contracts describing obsolete concepts. It also says the debt
becomes *measurable* rather than subjective.

Nothing measured it. The contract tests of this package assert
that a Protocol declares its own methods — `callable(Registry.get)`
— which is a tautology: a Protocol always declares what it
declares. Not one of them asks whether anything satisfies it.

`isinstance` cannot answer either: these Protocols are not
`runtime_checkable`, and making them so would only check method
names, not signatures.

So the check is structural and explicit.
"""

from __future__ import annotations

import inspect


IGNORED_BASES = {"Protocol", "Generic", "object"}


def protocol_members(protocol: type) -> set[str]:
    """
    The names a Protocol requires, including the ones it
    inherits.

    Read from the Protocol's own namespaces rather than from
    `__protocol_attrs__`, which is a CPython internal added in
    3.12 — a test that used it silently required that version.

    The walk over `__mro__` is the whole point. `MutableRegistry`
    extends `Registry`, so it requires five members; reading only
    its own namespace reports two, and a conformance check that
    under-reports what a contract demands is the same failure it
    was written to catch.
    """

    required: set[str] = set()

    for base in protocol.__mro__:

        if base.__name__ in IGNORED_BASES:
            continue

        required.update(
            name
            for name in vars(base)
            if not name.startswith("_")
        )

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

        expected = getattr(protocol, name)
        actual = getattr(implementation, name)

        if not callable(expected):
            continue

        if not callable(actual):
            problems[name] = "declared callable, implemented as a value"
            continue

        want = inspect.signature(expected)
        have = inspect.signature(actual)

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


def assert_implements(protocol: type, implementation: type) -> None:

    missing = missing_members(protocol, implementation)

    assert not missing, (
        f"{implementation.__name__} does not implement "
        f"{protocol.__name__}: missing {sorted(missing)}"
    )

    problems = incompatible_members(protocol, implementation)

    assert not problems, (
        f"{implementation.__name__} does not match "
        f"{protocol.__name__}: {problems}"
    )
