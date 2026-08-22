"""
Assertion helper over the product's conformance primitives.

The structural comparison itself now lives in
`aistack.conformance.structural`, promoted out of this tree on
2026-08-22 (GOV-0002/OS-002). What stays here is the one thing
that is genuinely test scaffolding: turning a report into an
assertion with a message a reader can act on.

Why the comparison had to leave: FDN-0011 makes technical debt a
property of the contracts and requires it to be *derived*. The
only code able to decide whether a class satisfies a Protocol was
in the test tree, so the product could not measure its own
contracts, and the seventeen orphan contracts of GOV-0002/OS-001
were an agent's assertion rather than a published measurement.

Why these tests exist at all: the contract tests of this package
used to assert that a Protocol declares its own methods —
`callable(Registry.get)` — which is a tautology. A Protocol always
declares what it declares. Not one of them asked whether anything
satisfied it.
"""

from aistack.conformance.structural import (
    incompatible_members,
    missing_members,
    protocol_members,
)


__all__ = [
    "assert_implements",
    "incompatible_members",
    "missing_members",
    "protocol_members",
]


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
