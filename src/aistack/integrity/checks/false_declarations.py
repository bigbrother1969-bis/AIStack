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
    inventory measured what a class provides and, until
    2026-08-28, never consulted what it said it was. A
    declaration false about itself produced a finding nowhere.

    So this reads the other half of the same inventory —
    `declared_by` against `satisfied_by` — and needs no new
    primitive: OS-040 says the condition is derivable *cheaply*,
    and it is `satisfies()` called in the direction nothing called
    it in.

    **`WARNING`, raised 2026-08-28 in the commit that brought the
    count to 0 of 40, and not before.** The owner qualified a
    false declaration that day as **a defect of the heritage**:
    STD-P-002 makes a contract ahead of its implementation the
    prescribed order, which is what keeps an orphan contract a
    fact rather than a fault, and a class *claiming* a contract it
    does not honour is on the other side of that line — not
    deferred work, but a statement about the code that the code
    contradicts.

    It was introduced at `OBSERVATION` for one commit, with the
    count at 1 of 40, for the reason 2026-08-27 established: a
    check turned red in the commit that introduces it forbids
    publishing its own repair, since OPS-0002 § 1 makes
    `clean: True` a condition of publishing. Second entry to use
    that sequencing, after `unfinished-decisions`.

    From here a false declaration holds the heritage at
    `clean: False` until an open register entry names it, which is
    OPS-0002 § 1 working as written. The suite refuses it first —
    `test_no_class_declares_a_contract_it_does_not_satisfy` — so
    the `WARNING` is what remains for a projection produced
    elsewhere, or by a pipeline that skipped the suite.

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
                severity=IntegritySeverity.WARNING,
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
