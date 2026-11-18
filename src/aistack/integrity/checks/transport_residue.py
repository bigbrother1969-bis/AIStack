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

        # A source is relative to the root of the heritage
        # (GOV-0002/OS-096) and a bundle generated before that is
        # absolute. The locations start with a separator, so the
        # source is read with one in front: `docs/incoming/x.md`
        # must match as `/srv/x/docs/incoming/x.md` does, and
        # `mydocs/incoming/x.md` must not.
        subjects = tuple(
            artifact.source
            for artifact in bundle.artifacts
            if any(
                location in f"/{artifact.source.lstrip('/')}"
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
