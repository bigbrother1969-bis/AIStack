"""
A class that names an abstract base and implements none of it is
neither a contract nor an implementation.

**Nine of them lived in the Kernel from 2026-07 until 2026-08-29.**
`kernel/capabilities/package/` held `CompressCapability`,
`HashCapability`, `SignCapability` and six more, each written as

    class CompressCapability(PackageCapability):
        pass

`PackageCapability` is an ABC with two `@abstractmethod`s, so
**none of the nine could be instantiated** — every one raised
`TypeError: Can't instantiate abstract class ... with abstract
methods process, supports`. They were not unused. They were
unusable.

**`contract-debt` had been reporting them all along, and nobody
read it that way.** Removing the nine moved it from *13 of 50
declared contracts satisfied by no class* to *4 of 41*: a class
with unimplemented abstract methods **is** a declared contract by
this heritage's definition, so each empty subclass was inventoried
as one and published as an orphan at every projection for five
weeks. The check cannot tell *a contract written before its
implementation* — STD-P-002's prescribed order — from *an
implementation that implements nothing*, and ten of those orphans
had been qualified `planned` on 2026-08-23. **The nine sat inside
a figure already declared acceptable.**

The other two instruments said nothing, correctly:

- `false-declarations` reports a class naming a base it does not
  satisfy. The base **is** satisfied structurally, so it saw
  nothing either;
- `tests/unit/kernel/test_package_capabilities.py` asserted
  `issubclass(capability, PackageCapability)` under the name
  *test_package_capabilities_implement_contract*. **`issubclass`
  is true of a declaration and says nothing about an
  implementation** — the identical mistake this heritage recorded
  on 2026-08-28 for `SshBundleTransfer`, where a test asserted the
  declaration and the claim was `satisfies`. Second occurrence,
  found by measurement rather than by reading.

`ADR-0008` had qualified the row *Capability, PackageCapability
and nine implementations* as `done` on 2026-08-27. The nine were
removed on 2026-08-29 under ARC-P-006 and the row re-qualified.

**What this test guards is the shape, not those nine names.** The
contract stays: when a real packaging operation arrives it will be
written against `PackageCapability`, and this refuses the
intermediate step of declaring it and stopping there.
"""

from __future__ import annotations

import importlib
import inspect
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[3]


def tracked_modules() -> list[str]:
    """
    The repository's modules, not the working tree's — the
    distinction GOV-0002/OS-001 recorded and OS-044 paid for
    again.
    """

    output = subprocess.check_output(
        ["git", "ls-files", "src/**/*.py"],
        cwd=ROOT,
        text=True,
    )

    names = []

    for path in output.splitlines():
        name = path[len("src/") : -len(".py")].replace("/", ".")

        if name.endswith(".__init__"):
            name = name[: -len(".__init__")]

        names.append(name)

    return names


def declared_classes():
    """Every class this heritage defines, once each."""

    seen = {}

    for name in tracked_modules():
        try:
            module = importlib.import_module(name)
        except Exception:
            # An import that fails is a different defect and has
            # its own tests. Silence here would hide it, so it is
            # reported by the check below rather than swallowed.
            continue

        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__.startswith("aistack"):
                seen[f"{cls.__module__}.{cls.__name__}"] = cls

    return seen


def empty_declarations() -> list[str]:
    """
    Classes left abstract by inheritance alone.

    A legitimate abstract base **declares** its own abstract
    methods, so its `__abstractmethods__` come from its own body.
    A class that adds nothing and implements nothing has abstract
    methods it neither wrote nor filled — which is the whole
    signature of the nine.
    """

    offenders = []

    for qualified, cls in declared_classes().items():
        abstract = getattr(cls, "__abstractmethods__", frozenset())

        if not abstract:
            continue

        declared_here = {
            name
            for name in abstract
            if name in cls.__dict__
        }

        if not declared_here:
            offenders.append(qualified)

    return sorted(offenders)


def test_no_class_declares_a_contract_and_implements_nothing():
    """
    Mutation 2026-08-29: restoring
    `class CompressCapability(PackageCapability): pass` turns this
    red. Every abstract base currently in the heritage declares
    its own abstract methods and is untouched by it.
    """

    offenders = empty_declarations()

    assert offenders == [], (
        f"{offenders} name an abstract base and implement none of it, "
        f"so they cannot be instantiated. contract-debt will count each "
        f"as one more orphaned contract — which is true and is not what "
        f"they are"
    )


def test_the_rule_is_measured_over_a_heritage_that_can_break_it():
    """
    The test above passes on a heritage with no abstract classes
    at all, and from a report that is indistinguishable from a
    clean one — the lesson `false-declarations` was given on
    2026-08-28.

    So the floor is stated: **at least twenty abstract bases were
    declared on 2026-08-29**, each defining its own abstract
    methods. A refactor that stopped importing them, or that
    replaced ABCs with Protocols throughout, would leave the rule
    true and verifying nothing.
    """

    bases = [
        cls
        for cls in declared_classes().values()
        if getattr(cls, "__abstractmethods__", frozenset())
    ]

    assert len(bases) >= 20
