from collections import defaultdict

from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)
from aistack.contracts.undeclared import UNDECLARED


class DuplicateTitleCheck(IntegrityCheck):
    """
    A bundle section title is how a human or an agent refers
    to an artifact.

    When several artifacts share a title, a reference to it
    is ambiguous and only the content hash disambiguates.

    Artifacts declaring no title are skipped. They all carry
    UNDECLARED, which would collide with itself and turn this
    check into a second, noisier report of what
    `metadata-completeness` already says. An absent title is a
    missing declaration; it is not a collision.
    """

    @property
    def name(self) -> str:
        return "duplicate-titles"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        by_title = defaultdict(list)

        for artifact in bundle.artifacts:

            if artifact.title == UNDECLARED:
                continue

            by_title[artifact.title].append(artifact.source)

        collisions = {
            title: sources
            for title, sources in by_title.items()
            if len(sources) > 1
        }

        if not collisions:
            return []

        affected = sum(
            len(sources)
            for sources in collisions.values()
        )

        subjects = tuple(
            f"{title} ({len(sources)})"
            for title, sources in sorted(collisions.items())
        )

        return [
            IntegrityFinding(
                check=self.name,
                severity=IntegritySeverity.WARNING,
                summary=(
                    "artifacts share a title with at least one "
                    "other artifact"
                ),
                affected=affected,
                total=len(bundle.artifacts),
                subjects=subjects,
            )
        ]
