from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


TRANSIT_LOCATIONS = (
    "/docs/incoming/",
    "/99-meta/integration/",
)


class TransportResidueCheck(IntegrityCheck):
    """
    No temporary transport artifact should remain inside the
    operational heritage.

    A document staged in transit has not passed the
    validation gate, yet a bundle projects it exactly like a
    governed one.
    """

    @property
    def name(self) -> str:
        return "transport-residue"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        subjects = tuple(
            artifact.source
            for artifact in bundle.artifacts
            if any(
                location in artifact.source
                for location in TRANSIT_LOCATIONS
            )
        )

        if not subjects:
            return []

        return [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.WARNING,
                summary=(
                    "artifacts are projected from a transit "
                    "location rather than the governed heritage"
                ),
                affected=len(subjects),
                total=len(bundle.artifacts),
                subjects=subjects,
            )
        ]
