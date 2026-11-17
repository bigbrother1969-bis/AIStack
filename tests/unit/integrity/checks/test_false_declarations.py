from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from aistack.conformance.inventory import take_inventory
from aistack.conformance.serialization import (
    deserialize_inventory,
    serialize_inventory,
)
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.contract_inventory import (
    ABSTRACT,
    PROTOCOL,
    ContractInventory,
    DeclaredContract,
)
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.false_declarations import (
    FalseDeclarationCheck,
)


NOW = datetime(2026, 8, 28, 12, 0, 0)


def bundle(inventory=None) -> ContextBundle:
    return ContextBundle(
        id="test-bundle",
        title="Test",
        generated_at=NOW,
        source_commit="abc1234",
        contract_inventory=inventory,
    )


def inventory(*contracts, measured: bool = True) -> ContractInventory:
    return ContractInventory(
        package="aistack",
        modules=300,
        implementations=150,
        contracts=contracts,
        declarations_measured=measured,
    )


def contract(name, satisfied=(), declared=()) -> DeclaredContract:
    return DeclaredContract(
        name=name,
        module="m",
        kind=ABSTRACT,
        members=("transfer",),
        satisfied_by=satisfied,
        declared_by=declared,
    )


# --------------------------------------------------------------------
# The condition
# --------------------------------------------------------------------


def test_a_class_declaring_a_base_it_does_not_satisfy_is_reported():
    """
    The shape of GOV-0002/OS-040. `SshBundleTransfer` named its
    contract as a base and implemented a different signature; the
    ABC machinery let it instantiate, and nothing reported the
    declaration.
    """

    findings = FalseDeclarationCheck().evaluate(
        bundle(
            inventory(
                contract(
                    "Service",
                    satisfied=("m.Honest",),
                    declared=("m.Honest", "m.Liar"),
                )
            )
        )
    )

    assert len(findings) == 1
    assert findings[0].affected == 1
    assert findings[0].total == 2
    assert findings[0].subjects == ("m.Liar declares m.Service",)


def test_a_class_that_satisfies_what_it_declares_is_not_reported():

    findings = FalseDeclarationCheck().evaluate(
        bundle(
            inventory(
                contract(
                    "Service",
                    satisfied=("m.Honest",),
                    declared=("m.Honest",),
                )
            )
        )
    )

    assert findings == []


def test_satisfying_without_declaring_is_not_this_check_s_business():
    """
    Structural conformance is `contract-debt`'s question. A class
    satisfying a Protocol it never names is the normal case for a
    Protocol, and reporting it here would turn a check about
    declarations into a second, worse implementation inventory.
    """

    findings = FalseDeclarationCheck().evaluate(
        bundle(
            inventory(
                contract("Service", satisfied=("m.Structural",))
            )
        )
    )

    assert findings == []


def test_an_orphan_contract_nobody_declares_produces_nothing_here():
    """
    `contract-debt` publishes that one. Two checks reporting one
    fact is how a report doubles without measuring more.
    """

    findings = FalseDeclarationCheck().evaluate(
        bundle(inventory(contract("Orphan")))
    )

    assert findings == []


# --------------------------------------------------------------------
# Not measured is not zero
# --------------------------------------------------------------------


def test_an_inventory_taken_before_declarations_were_measured_says_so():
    """
    A projection published before 2026-08-28 carries no
    `declared_by`. Reading its silence as *no false declaration*
    would let "nothing found" and "nobody looked" print
    identically — the failure this heritage has already paid for
    twice, over a tree the walk could not see.
    """

    findings = FalseDeclarationCheck().evaluate(
        bundle(
            inventory(
                contract("Service", satisfied=("m.Honest",)),
                measured=False,
            )
        )
    )

    assert len(findings) == 1
    assert "undeclared, not zero" in findings[0].summary
    assert findings[0].severity is IntegritySeverity.OBSERVATION


def test_a_bundle_with_no_inventory_is_left_to_contract_debt():
    """
    `contract-debt` already publishes a missing inventory in those
    words. Saying it twice doubles every report produced from an
    older bundle.
    """

    assert FalseDeclarationCheck().evaluate(bundle()) == []


# --------------------------------------------------------------------
# The severity is a decision, and it is watched
# --------------------------------------------------------------------


def test_the_finding_carries_the_severity_the_owner_decided():
    """
    `WARNING`, raised 2026-08-28 in the commit that brought the
    count to 0 of 40 and not before.

    The owner qualified a false declaration that day as **a defect
    of the heritage**: STD-P-002 makes a contract ahead of its
    implementation the prescribed order, which keeps an orphan
    contract a fact rather than a fault, and a class claiming a
    contract it does not honour is on the other side of that line.

    It lived one commit at `OBSERVATION`, with the count at 1 of
    40, because a check turned red in the commit that introduces
    it forbids publishing its own repair under OPS-0002 § 1.

    **The unmeasured finding below stays `OBSERVATION`**, and the
    two are asserted separately: *nobody looked* is not *somebody
    lied*, and a projection that predates the measurement must not
    hold this heritage at `clean: False`.
    """

    findings = FalseDeclarationCheck().evaluate(
        bundle(
            inventory(
                contract(
                    "Service",
                    satisfied=("m.Honest",),
                    declared=("m.Honest", "m.Liar"),
                )
            )
        )
    )

    assert findings[0].severity is IntegritySeverity.WARNING


# --------------------------------------------------------------------
# The measurement itself
# --------------------------------------------------------------------


class Carrier(ABC):
    """A contract of this test module, not of the heritage."""

    @abstractmethod
    def transfer(self, bundle_path: Path) -> bool:
        ...


class Renamer(Carrier):
    """Declares `Carrier` and renames its parameter."""

    def transfer(self, source: Path) -> bool:
        return True


def test_a_planted_false_declaration_is_found_by_name():
    """
    **The control test.** A check that stopped finding anything
    and a heritage with nothing to find print the same report, so
    the instrument is exercised on a case built to be caught.

    `Renamer` satisfies the ABC as far as Python is concerned —
    it instantiates — and differs from its declared contract by
    one parameter name, which is exactly the divergence
    GOV-0002/OS-040 was opened on.
    """

    Renamer()  # the language raises nothing; that is the subject

    from aistack.conformance.structural import (
        incompatible_members,
        missing_members,
    )

    assert missing_members(Carrier, Renamer) == set()
    assert "transfer" in incompatible_members(Carrier, Renamer)

    findings = FalseDeclarationCheck().evaluate(
        bundle(
            inventory(
                contract(
                    "Carrier",
                    satisfied=(),
                    declared=("m.Renamer",),
                )
            )
        )
    )

    assert findings[0].subjects == ("m.Renamer declares m.Carrier",)


def test_the_inventory_reads_what_a_class_says_it_is():
    """
    `declared_by` comes from `__mro__` and `satisfied_by` from the
    call shapes. The two are separate measurements, and this
    asserts the first is taken over the real package rather than
    defaulting to empty.
    """

    taken = take_inventory("aistack")

    assert taken.declarations_measured
    assert taken.declaring > 0

    declaring = {
        contract.qualified_name: contract.declared_by
        for contract in taken.contracts
        if contract.declared_by
    }

    assert declaring, "no class declares a contract of this heritage"


def test_a_contract_refining_a_contract_does_not_declare_it():
    """
    `MutableRegistry` extends `Registry`. A Protocol extending a
    Protocol refines a contract; it does not claim to implement
    one, and counting it would report the contract architecture's
    own shape as debt.
    """

    taken = take_inventory("aistack")

    for contract in taken.contracts:
        assert "MutableRegistry" not in " ".join(contract.declared_by)


def test_the_declarations_survive_the_projection():
    """
    The measurement is taken where the source tree is and read
    where only the bundle is. A field that did not travel would
    make the check silent on every published projection.
    """

    original = inventory(
        contract(
            "Service",
            satisfied=("m.Honest",),
            declared=("m.Honest", "m.Liar"),
        )
    )

    restored = deserialize_inventory(serialize_inventory(original))

    assert restored.declarations_measured
    assert restored.contracts[0].declared_by == ("m.Honest", "m.Liar")
    assert restored.false_declarations == (("m.Liar", "m.Service"),)


def test_a_payload_without_declarations_restores_as_unmeasured():
    """
    A 1.0 payload. `declarations_measured` False rather than an
    empty list read as an answer.
    """

    payload = serialize_inventory(inventory(contract("Service")))
    del payload["declarations_measured"]

    for entry in payload["contracts"]:
        del entry["declared_by"]

    restored = deserialize_inventory(payload)

    assert not restored.declarations_measured
    assert restored.contracts[0].declared_by == ()


def test_a_protocol_kind_is_read_the_same_way():
    """
    Both kinds of contract are in scope. A check that saw only
    ABCs would miss every Protocol the heritage declares, which is
    most of them.
    """

    findings = FalseDeclarationCheck().evaluate(
        bundle(
            inventory(
                DeclaredContract(
                    name="Shaped",
                    module="m",
                    kind=PROTOCOL,
                    members=("send",),
                    satisfied_by=(),
                    declared_by=("m.Claimant",),
                )
            )
        )
    )

    assert findings[0].subjects == ("m.Claimant declares m.Shaped",)
