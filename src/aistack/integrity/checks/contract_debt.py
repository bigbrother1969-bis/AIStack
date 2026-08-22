from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


class ContractDebtCheck(IntegrityCheck):
    """
    Publish the contract architecture the projection carries.

    FDN-0011 defines technical debt as a property of the
    contracts and requires it to be *derived from violations of
    the contract architecture rather than from subjective code
    reviews*. Until 2026-08-22 nothing derived it: the seventeen
    orphan contracts recorded in GOV-0002/OS-001 were an agent's
    assertion, produced once by a script that no longer exists.

    This check publishes the derivation at every projection.
    That is the difference FDN-P-014 turns on — a figure anyone
    can obtain from the bundle alone, rather than one someone
    remembered to measure.

    **Every finding is an OBSERVATION, and that is a decision,
    not a default.** STD-P-002 makes a contract written ahead of
    its implementation the prescribed order; an orphan contract
    is therefore a fact, not a fault, and which orphans are
    planned and which abandoned is a qualification GOV-P-001
    places with the owner. `KnowledgeIntegrityReport.is_clean`
    ignores observations for exactly this reason: *they state
    facts that are not yet governed rules*.

    Raising them to WARNING would also make STD-0300 criterion
    2.6 fail on twenty facts the heritage has decided are not
    faults — a check inventing a verdict the standard never gave
    it.
    """

    @property
    def name(self) -> str:
        return "contract-debt"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        inventory = bundle.contract_inventory

        if inventory is None:
            # Not measured is not zero. A bundle produced by an
            # older pipeline, or by a caller with no source tree
            # to walk, carries no inventory — a governed state
            # under FDN-0003 Article 12. Reporting nothing here
            # would let "no orphan contracts" and "nobody looked"
            # read identically, which is the failure this
            # heritage keeps paying for.
            return [
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        "this projection carries no contract "
                        "inventory; the contract debt is "
                        "undeclared, not zero"
                    ),
                    affected=0,
                    total=0,
                    unit="declared contracts",
                )
            ]

        findings = [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.OBSERVATION,
                summary=(
                    f"{len(inventory.orphans)} of "
                    f"{len(inventory.contracts)} declared "
                    f"contracts are satisfied by no class among "
                    f"{inventory.implementations} "
                    f"(STD-P-002 makes this an order, not a fault; "
                    f"qualification belongs to the owner)"
                ),
                affected=len(inventory.orphans),
                total=len(inventory.contracts),
                unit="declared contracts",
                subjects=tuple(
                    contract.qualified_name
                    for contract in inventory.orphans
                ),
            )
        ]

        if inventory.is_partial:
            # The module that did not import may hold the very
            # class that satisfies a contract counted above, so
            # the orphan figure is an upper bound. Saying so is
            # the whole difference between a measurement and a
            # number.
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(inventory.unreadable)} module(s) "
                        f"could not be imported when the "
                        f"inventory was taken; the orphan count "
                        f"above is an upper bound"
                    ),
                    affected=len(inventory.unreadable),
                    total=inventory.modules,
                    unit="modules",
                    subjects=tuple(
                        module for module, _ in inventory.unreadable
                    ),
                )
            )

        return findings
