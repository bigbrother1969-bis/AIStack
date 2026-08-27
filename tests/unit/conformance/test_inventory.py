from abc import ABC, abstractmethod
from typing import Protocol

import pytest

from aistack.conformance.inventory import (
    classes_of,
    is_contract,
    take_inventory,
)
from aistack.contracts.contract_inventory import (
    ABSTRACT,
    PROTOCOL,
    ContractInventory,
    DeclaredContract,
)


# --------------------------------------------------------------------
# What counts as a contract
# --------------------------------------------------------------------


def test_a_protocol_is_a_contract():

    class Store(Protocol):
        def get(self, key: str) -> object: ...

    assert is_contract(Store) == PROTOCOL


def test_an_abc_with_abstract_methods_is_a_contract():
    """
    Seven integrity checks implement an ABC. A pass that
    recognised only `Protocol` reported `IntegrityCheck` as an
    orphan while seven classes implemented it — one of the three
    wrong measurements this module exists to replace.
    """

    class Check(ABC):
        @abstractmethod
        def evaluate(self) -> list:
            raise NotImplementedError

    assert is_contract(Check) == ABSTRACT


def test_a_concrete_class_is_not_a_contract():

    class Plain:
        def get(self, key: str) -> object:
            return None

    assert is_contract(Plain) is None


def test_an_abc_whose_methods_are_all_implemented_is_not_a_contract():
    """
    Inheriting from ABC declares nothing. What makes a class a
    contract is having members nobody has implemented.
    """

    class NotReallyAbstract(ABC):
        def evaluate(self) -> list:
            return []

    assert is_contract(NotReallyAbstract) is None


def test_a_contract_that_requires_nothing_is_not_a_contract():
    """
    An empty Protocol is satisfied by every class in the package,
    so counting it says nothing — and counting it as *satisfied*
    inflates the number of honoured contracts.

    Found on the real package: the two empty Protocols that
    `aistack.conformance.structural` uses to measure what a
    Protocol carries were inventoried as contracts of the
    heritage, each satisfied by all 144 concrete classes. The
    instrument was counting itself.
    """

    class Empty(Protocol):
        pass

    assert is_contract(Empty) is None


# --------------------------------------------------------------------
# What a module contributes
# --------------------------------------------------------------------


def test_only_classes_a_module_defines_are_counted():
    """
    Filtering on `__module__` is what stops a class being counted
    once per module that imports it. A contract counted twice
    inflates the debt.
    """

    import aistack.conformance.inventory as subject

    defined = {c.__name__ for c in classes_of(subject, "aistack")}

    assert "ContractInventory" not in defined
    assert "DeclaredContract" not in defined


# --------------------------------------------------------------------
# The model
# --------------------------------------------------------------------


def test_a_contract_nothing_satisfies_is_an_orphan():
    """
    Named after a real orphan, and kept that way on purpose.

    This fixture read `TransferTarget` until 2026-08-27, when that
    contract was removed as superseded by
    `BundleTransferConfiguration` — and the fixture went on naming a
    module that no longer existed, in a test file about measuring
    the package. A fixture that cites a deleted module is a stale
    assertion like any other.
    """

    contract = DeclaredContract(
        name="EvidenceCollector",
        module="aistack.evidence.collectors",
        kind=ABSTRACT,
        members=("acquire",),
    )

    assert contract.is_orphan
    assert contract.qualified_name == (
        "aistack.evidence.collectors.EvidenceCollector"
    )


def test_a_contract_something_satisfies_is_not_an_orphan():

    contract = DeclaredContract(
        name="IntegrityCheck",
        module="aistack.contracts.integrity_check",
        kind=ABSTRACT,
        members=("evaluate", "name"),
        satisfied_by=("aistack.integrity.checks.x.XCheck",),
    )

    assert not contract.is_orphan


def test_a_contract_declares_a_kind_the_vocabulary_contains():

    with pytest.raises(ValueError, match="protocol"):
        DeclaredContract(name="X", module="m", kind="interface")


def test_the_same_contract_may_not_be_counted_twice():
    """
    A contract counted twice inflates the debt, and the debt is
    the whole output.
    """

    contract = DeclaredContract(name="X", module="m", kind=PROTOCOL)

    with pytest.raises(ValueError, match="twice"):
        ContractInventory(
            package="aistack",
            modules=1,
            implementations=0,
            contracts=(contract, contract),
        )


def test_an_inventory_with_an_unreadable_module_is_partial():
    """
    The module that did not import may hold the very class that
    satisfies a contract counted as orphan. A partial inventory
    reports orphans *at most*.

    Two earlier measurements of this heritage walked past
    `src/aistack/integrity/` and published a complete inventory
    of a tree they could not see.
    """

    partial = ContractInventory(
        package="aistack",
        modules=10,
        implementations=3,
        unreadable=(("aistack.funnel.__main__", "ModuleNotFoundError"),),
    )

    assert partial.is_partial

    complete = ContractInventory(
        package="aistack", modules=10, implementations=3
    )

    assert not complete.is_partial


# --------------------------------------------------------------------
# Against the real package
# --------------------------------------------------------------------


def test_the_integrity_checks_satisfy_their_contract():
    """
    The control case, and it is not decorative: an earlier pass
    reported `IntegrityCheck` as an orphan while seven classes
    implemented it. If this inventory ever answers otherwise, it
    is measuring nominal inheritance or has lost the ABC branch.
    """

    inventory = take_inventory()

    check = next(
        c for c in inventory.contracts if c.name == "IntegrityCheck"
    )

    assert not check.is_orphan
    assert len(check.satisfied_by) == 13
    assert all(
        "integrity.checks" in name for name in check.satisfied_by
    )

    # `contract-debt` is the eighth, and it is the one that
    # publishes this very inventory. The check appearing in the
    # measurement it produces is not the instrument counting
    # itself: it is a governed component of the product, exactly
    # like the seven before it.
    assert any(
        name.endswith("ContractDebtCheck")
        for name in check.satisfied_by
    )


def test_the_inventory_does_not_declare_everything_orphan():
    """
    The other direction. A discovery that failed to recognise any
    implementation would report every contract as an orphan and
    look like a very thorough audit.
    """

    inventory = take_inventory()

    assert inventory.contracts
    assert inventory.orphans
    assert len(inventory.orphans) < len(inventory.contracts)


def test_every_module_of_the_package_imports():
    """
    The inventory of this repository is complete, and that is a
    governed fact rather than a happy accident.

    Until 2026-08-23 it was partial: `aistack.funnel.__main__`
    imported a `core.py` that had never been committed
    (GOV-0002/OS-018), so the orphan count was an upper bound.
    The module was removed and the count became a count.

    This test replaces the one that asserted the opposite. That
    one carried, in its own docstring, the sentence *"when
    OS-018 is closed this test fails, and that is the point"* —
    a test written to be killed by the repair it was watching
    for.

    What it protects now is the other direction: a module that
    stops importing makes every orphan figure an upper bound
    again, and this says so by name rather than letting the
    report quietly grow a caveat.
    """

    inventory = take_inventory()

    assert inventory.unreadable == (), (
        f"the package no longer imports cleanly: "
        f"{[m for m, _ in inventory.unreadable]}"
    )

    assert not inventory.is_partial
