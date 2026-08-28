from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


class FalseDeclarationCheck(IntegrityCheck):
    """
    Observe a class declaring a contract it does not satisfy.

    `SshBundleTransfer` named `BundleTransfer` as a base from the
    day it was written until 2026-08-27 and implemented a
    different method:

    ```text
    def transfer(self, source: Path, target: str) -> bool   # the contract
    def transfer(self, source: Path) -> bool                # what it had
    ```

    Python's ABC machinery checks that a method of the right
    *name* exists and never looks at the signature, so the class
    instantiated happily while `DefaultContextBundleService` went
    on annotating its parameter with a contract production did not
    honour. GOV-0002/OS-040.

    **The heritage's own instrument was never fooled, and that is
    the finding.** `aistack.conformance.structural.satisfies`
    compares call shapes, so `contract-debt` never counted that
    class among the contract's implementations and never had to.
    What no instrument reported was the **declaration**: the
    inventory measures what a class provides and, until
    2026-08-28, never consulted what it says it is. A declaration
    false about itself produced a finding nowhere.

    So this reads the other half of the same inventory —
    `declared_by` against `satisfied_by` — and needs no new
    primitive: OS-040 says the condition is derivable *cheaply*,
    and it is `satisfies()` called in the direction nothing called
    it in.

    **`OBSERVATION`, and the alternative is named rather than
    silent.** The condition is a fault and not an order — a class
    lying about itself is not STD-P-002's *specification before
    implementation* — so `WARNING` is defensible. It is not taken
    here for the reason 2026-08-27 established: a check turned red
    in the commit that introduces it forbids publishing its own
    repair, since OPS-0002 § 1 makes `clean: True` a condition of
    publishing. The severity question belongs to the commit that
    brings the count to zero, which is where
    `unfinished-decisions` answered it.

    **What it does not see.** A class satisfying a contract
    without naming it is invisible here and is meant to be:
    structural conformance is `contract-debt`'s question. And a
    projection taken before 2026-08-28 carries no declarations at
    all — reported as undeclared rather than as zero, because
    *not measured is not zero* is what an inventory that walked a
    tree it could not see already cost this heritage twice.
    """

    @property
    def name(self) -> str:
        return "false-declarations"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        inventory = bundle.contract_inventory

        if inventory is None:
            # `contract-debt` already publishes the absence of an
            # inventory, in those words. Repeating it here would
            # put one fact in two findings and double every report
            # produced from an older bundle.
            return []

        if not inventory.declarations_measured:
            return [
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        "this projection's contract inventory "
                        "carries no declarations; false "
                        "declarations are undeclared, not zero"
                    ),
                    affected=0,
                    total=len(inventory.contracts),
                    unit="declarations",
                )
            ]

        false = inventory.false_declarations

        if not false:
            return []

        return [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.OBSERVATION,
                summary=(
                    f"{len(false)} of {inventory.declaring} "
                    f"class-contract declaration(s) name a base "
                    f"the class does not satisfy"
                ),
                affected=len(false),
                total=inventory.declaring,
                unit="declarations",
                subjects=tuple(
                    f"{implementation} declares {contract}"
                    for implementation, contract in false
                ),
            )
        ]
