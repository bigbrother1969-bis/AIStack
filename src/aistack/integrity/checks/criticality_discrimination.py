from collections import Counter

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


class CriticalityDiscriminationCheck(IntegrityCheck):
    """
    The README bootstrap protocol requires a Criticality
    Evaluation step.

    That step is not executable when every artifact carries
    the same criticality: there is nothing to evaluate.
    """

    @property
    def name(self) -> str:
        return "criticality-discrimination"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        total = len(bundle.artifacts)

        if not total:
            return []

        distribution = Counter(
            artifact.criticality
            for artifact in bundle.artifacts
        )

        if len(distribution) > 1:
            return []

        level = next(iter(distribution))

        return [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.BLOCKING,
                summary=(
                    "every artifact carries the same criticality "
                    f"(C{level}); criticality evaluation cannot "
                    "be performed"
                ),
                affected=total,
                total=total,
            )
        ]
