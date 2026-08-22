from datetime import datetime

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.contract_inventory import (
    ABSTRACT,
    PROTOCOL,
    ContractInventory,
    DeclaredContract,
)
from aistack.contracts.integrity_finding import IntegritySeverity
from aistack.integrity.checks.contract_debt import ContractDebtCheck


NOW = datetime(2026, 8, 22, 12, 0, 0)


def bundle(inventory=None) -> ContextBundle:
    return ContextBundle(
        id="test-bundle",
        title="Test",
        generated_at=NOW,
        source_commit="abc1234",
        contract_inventory=inventory,
    )


def inventory(**overrides) -> ContractInventory:
    declared = {
        "package": "aistack",
        "modules": 300,
        "implementations": 145,
        "contracts": (
            DeclaredContract(
                name="Satisfied",
                module="m",
                kind=ABSTRACT,
                members=("evaluate",),
                satisfied_by=("m.Impl",),
            ),
            DeclaredContract(
                name="Orphan",
                module="m",
                kind=PROTOCOL,
                members=("send",),
            ),
        ),
    }
    declared.update(overrides)
    return ContractInventory(**declared)


def test_the_orphan_contracts_are_published_with_their_names():

    findings = ContractDebtCheck().evaluate(bundle(inventory()))

    assert len(findings) == 1
    assert findings[0].affected == 1
    assert findings[0].total == 2
    assert findings[0].subjects == ("m.Orphan",)


def test_every_finding_is_an_observation():
    """
    STD-P-002 makes a contract written ahead of its
    implementation the prescribed order, so an orphan is a fact
    and not a fault. `is_clean` ignores observations for exactly
    that reason.

    Raising these to WARNING would also fail STD-0300 criterion
    2.6 on twenty facts the heritage has decided are not faults —
    a check inventing a verdict the standard never gave it.
    """

    findings = ContractDebtCheck().evaluate(
        bundle(
            inventory(
                unreadable=(("m.broken", "ImportError: x"),)
            )
        )
    )

    assert len(findings) == 2
    assert all(
        f.severity is IntegritySeverity.OBSERVATION for f in findings
    )


def test_a_partial_inventory_says_the_count_is_an_upper_bound():
    """
    The module that did not import may hold the very class that
    satisfies a contract counted as orphan.
    """

    findings = ContractDebtCheck().evaluate(
        bundle(
            inventory(
                unreadable=(("m.broken", "ImportError: x"),)
            )
        )
    )

    assert "upper bound" in findings[1].summary
    assert findings[1].subjects == ("m.broken",)
    assert findings[1].unit == "modules"


def test_a_complete_inventory_claims_no_upper_bound():

    findings = ContractDebtCheck().evaluate(bundle(inventory()))

    assert not any("upper bound" in f.summary for f in findings)


def test_a_projection_without_an_inventory_says_undeclared_not_zero():
    """
    FDN-0003 Article 12. A bundle produced by an older pipeline,
    or read from a loose `bundle.json` where the inventory does
    not travel, carries none.

    Reporting nothing would let "no orphan contracts" and "nobody
    looked" read identically — the failure this heritage keeps
    paying for.
    """

    findings = ContractDebtCheck().evaluate(bundle(None))

    assert len(findings) == 1
    assert "undeclared, not zero" in findings[0].summary
    assert findings[0].severity is IntegritySeverity.OBSERVATION


def test_the_finding_names_what_it_counts():
    """
    The report printed `20/56 artifacts` for twenty orphan
    contracts in a heritage of 65 artifacts — a true count under
    a false name.
    """

    findings = ContractDebtCheck().evaluate(bundle(inventory()))

    assert findings[0].unit == "declared contracts"
