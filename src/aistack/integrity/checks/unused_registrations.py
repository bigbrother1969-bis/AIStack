from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


class UnusedRegistrationCheck(IntegrityCheck):
    """
    Publish what the Kernel registers and what asks for it.

    ADR-0004 § *Discovery Model*, restated by ARCH-0007: the
    Kernel is extended by registration, and application code
    requests capabilities from the Kernel Context rather than
    instantiating implementations. Both halves are facts about
    running code, and nothing measured either until 2026-08-28.

    **Three open register entries said the same thing in prose,
    from three different ADRs**, and all three carried *derivable
    partly, and by nothing that exists*:

    ```text
    OS-039  SelectionEngine        → 0 callers, 0 tests
            ByIdsSelectionStrategy → registered as `by-ids` and never retrieved
    OS-041  tasks registered       → 0
    OS-042  catalog_views          → 1 write site, 0 read sites
    ```

    Two of those three lines are registry facts, and this
    publishes them at every projection. GOV-0002/OS-001 named the
    three dimensions that place a contract — what implements it,
    what **consumes** it, what governs it — and said any one alone
    gives a confident wrong answer. The contract inventory
    measures the first. This is the second, for the one form of
    consumption the Kernel makes explicit.

    **Every finding is an `OBSERVATION`, and that is a decision.**
    STD-P-002 puts specification before implementation, so a
    capability registered ahead of its consumer is the prescribed
    order rather than a fault — the same reasoning that keeps
    `contract-debt` at `OBSERVATION` over thirteen orphan
    contracts. Which registrations are early and which are
    orphaned is a qualification, and GOV-P-001 places it with the
    owner: the three entries above are open on exactly that
    question and none of them is closed by this check. What
    changes is that the figures stop being sentences somebody
    maintains.

    **An empty registry is the sharper finding.** A registry the
    Kernel Context carries and the bootstrap leaves empty is not a
    capability waiting for a consumer; it is a resolver that
    cannot succeed. `TaskRegistry` is that on 2026-08-28, with
    `TaskResolver` asking it at every request.

    **A computed identifier is published rather than assumed
    away.** `self.tasks.get(context.request.task_id)` retrieves
    something this measurement cannot name, so everything in that
    registry is left out of the unretrieved count and the site is
    reported. Reading the count without that caveat would be
    reading an upper bound as a total, which is the mistake
    `contract-debt` publishes its own caveat to prevent.
    """

    @property
    def name(self) -> str:
        return "unused-registrations"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        inventory = bundle.registry_inventory

        if inventory is None or not inventory.measured:
            # Not measured is not zero. A projection produced by
            # an older pipeline, or by a caller with no repository
            # to read, carries no registrations — and a heritage
            # in which nothing is registered would look identical
            # from the report.
            return [
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        "this projection carries no registry "
                        "measurement; what the Kernel registers "
                        "and what retrieves it are undeclared, "
                        "not empty"
                    ),
                    affected=0,
                    total=0,
                    unit="registrations",
                )
            ]

        findings: list[IntegrityFinding] = []

        unretrieved = inventory.unretrieved

        if unretrieved:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(unretrieved)} of "
                        f"{len(inventory.registered)} registered "
                        f"identifier(s) are retrieved by nothing "
                        f"(STD-P-002 makes this an order, not a "
                        f"fault; qualification belongs to the "
                        f"owner)"
                    ),
                    affected=len(unretrieved),
                    total=len(inventory.registered),
                    unit="registrations",
                    subjects=tuple(
                        f"{entry.qualified_name} — {entry.entry}"
                        for entry in unretrieved
                    ),
                )
            )

        empty = inventory.empty_registries

        if empty:
            asked = {
                retrieval.registry
                for retrieval in inventory.retrievals
            }

            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(empty)} of "
                        f"{len(inventory.registries)} registries "
                        f"the Kernel Context carries hold nothing "
                        f"after bootstrap"
                    ),
                    affected=len(empty),
                    total=len(inventory.registries),
                    unit="registries",
                    subjects=tuple(
                        f"{registry} — "
                        + (
                            "asked by a retrieval site that cannot "
                            "succeed"
                            if registry in asked
                            else "nothing registers it and nothing "
                            "asks for it"
                        )
                        for registry in empty
                    ),
                )
            )

        tested_only = inventory.retrieved_only_in_tests

        if tested_only:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(tested_only)} registered "
                        f"identifier(s) are retrieved by tests and "
                        f"by nothing that ships"
                    ),
                    affected=len(tested_only),
                    total=len(inventory.registered),
                    unit="registrations",
                    subjects=tuple(
                        entry.qualified_name for entry in tested_only
                    ),
                )
            )

        computed = inventory.computed_sites

        if computed:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(computed)} retrieval site(s) name a "
                        f"computed identifier; what they resolve "
                        f"is outside this measurement and their "
                        f"registries are excluded from the count "
                        f"above"
                    ),
                    affected=len(computed),
                    total=len(inventory.retrievals),
                    unit="retrieval sites",
                    subjects=tuple(
                        f"{retrieval.site} — {retrieval.registry}"
                        for retrieval in computed
                    ),
                )
            )

        if inventory.is_partial:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.OBSERVATION,
                    summary=(
                        f"{len(inventory.unreadable)} source(s) "
                        f"could not be parsed when the "
                        f"registrations were measured; a retrieval "
                        f"may sit in one of them"
                    ),
                    affected=len(inventory.unreadable),
                    total=inventory.sources,
                    unit="sources",
                    subjects=tuple(
                        source for source, _ in inventory.unreadable
                    ),
                )
            )

        return findings
