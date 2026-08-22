"""
Walk a package and derive its contract architecture.

This is the derivation FDN-0011 asks for: *technical debt derived
from violations of the contract architecture rather than from
subjective code reviews*. What comes out is a count anyone can
reproduce, not an agent's reading.

Three measurements of this were wrong before this module existed,
and each mistake is a rule here:

- **nominal inheritance is meaningless.** A class satisfying a
  structural Protocol need not inherit from it. Counting
  subclasses reports orphans that are implemented and misses
  implementations that are wrong. Only the structural comparison
  of `aistack.conformance.structural` decides.
- **an ABC is a contract too.** A pass that recognised only
  `Protocol` reported `IntegrityCheck` as an orphan while seven
  checks implement it.
- **a module that does not import is not an absence.** Discovery
  that swallowed import failures reported a clean inventory of a
  tree it could not read. They are collected and published, and
  they make the inventory partial.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Protocol

from aistack.conformance.structural import protocol_members, satisfies
from aistack.contracts.contract_inventory import (
    ABSTRACT,
    PROTOCOL,
    ContractInventory,
    DeclaredContract,
)


def is_contract(subject: type) -> str | None:
    """
    The kind of contract a class is, or `None`.

    `Protocol` itself, `ABC` itself and the typing machinery are
    not contracts the heritage declares — they are the language's
    means of declaring one.
    """

    if subject in (Protocol, object):
        return None

    kind = None

    if getattr(subject, "_is_protocol", False):
        kind = PROTOCOL
    elif getattr(subject, "__abstractmethods__", frozenset()):
        kind = ABSTRACT

    if kind is None:
        return None

    # A contract that requires nothing is not a contract. It is
    # satisfied by every class in the package, so counting it
    # says nothing about anything, and counting it as *satisfied*
    # would inflate the number of honoured contracts.
    #
    # This is not a special case for one file. It was found
    # because of one: the two empty Protocols that
    # `aistack.conformance.structural` uses to measure what a
    # Protocol carries were themselves inventoried as contracts of
    # the heritage, each reported as satisfied by all 144 concrete
    # classes. The instrument was counting itself.
    if not protocol_members(subject):
        return None

    return kind


def classes_of(module: ModuleType, package: str) -> list[type]:
    """
    The classes a module defines, not the ones it imports.

    Filtering on `__module__` is what stops a class being counted
    once per module that imports it. A contract counted twice
    inflates the debt; an implementation counted twice does not
    change the answer but makes the totals unreproducible.
    """

    found = []

    for _, subject in inspect.getmembers(module, inspect.isclass):

        origin = getattr(subject, "__module__", "")

        if origin != module.__name__:
            continue

        if not origin.startswith(package):
            continue

        found.append(subject)

    return found


def take_inventory(package: str = "aistack") -> ContractInventory:
    """
    Import every module of `package` and derive its contracts.

    Importing is the only way to compare call shapes: a signature
    does not exist until the class does. The cost is that a broken
    module surfaces here — which is a feature, and how
    `aistack.funnel` was found after five weeks.
    """

    root = importlib.import_module(package)

    modules: list[ModuleType] = [root]
    unreadable: list[tuple[str, str]] = []

    for found in pkgutil.walk_packages(root.__path__, f"{package}."):
        try:
            modules.append(importlib.import_module(found.name))
        except Exception as error:
            # Deliberately broad. A module can fail to import for
            # reasons no narrower clause anticipates, and an
            # inventory that crashed on the first one would
            # measure nothing at all. Every failure is named in
            # the result, so nothing is swallowed.
            unreadable.append(
                (found.name, f"{type(error).__name__}: {error}")
            )

    contracts: dict[type, str] = {}
    concrete: list[type] = []

    for module in modules:
        for subject in classes_of(module, package):

            kind = is_contract(subject)

            if kind is None:
                concrete.append(subject)
            else:
                contracts[subject] = kind

    declared = tuple(
        DeclaredContract(
            name=contract.__name__,
            module=contract.__module__,
            kind=kind,
            members=tuple(sorted(protocol_members(contract))),
            satisfied_by=tuple(
                sorted(
                    f"{c.__module__}.{c.__name__}"
                    for c in concrete
                    if satisfies(contract, c)
                )
            ),
        )
        for contract, kind in sorted(
            contracts.items(),
            key=lambda item: (item[0].__module__, item[0].__name__),
        )
    )

    return ContractInventory(
        package=package,
        modules=len(modules),
        implementations=len(concrete),
        contracts=declared,
        unreadable=tuple(unreadable),
    )
