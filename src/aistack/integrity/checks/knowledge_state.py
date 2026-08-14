from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


UNKNOWN = "unknown"


class KnowledgeStateCheck(IntegrityCheck):
    """
    Knowledge state must be explicit.

    An artifact whose lifecycle status or confidence is
    undeclared cannot be distinguished from validated
    knowledge by a consuming agent.
    """

    @property
    def name(self) -> str:
        return "knowledge-state"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        total = len(bundle.artifacts)

        findings: list[IntegrityFinding] = []

        for field, severity in (
            ("status", IntegritySeverity.WARNING),
            ("confidence", IntegritySeverity.OBSERVATION),
        ):

            subjects = tuple(
                artifact.source
                for artifact in bundle.artifacts
                if getattr(artifact, field) == UNKNOWN
            )

            if subjects:
                findings.append(
                    IntegrityFinding(
                        check=self.name,
                        severity=severity,
                        summary=(
                            f"artifacts declare no {field}"
                        ),
                        affected=len(subjects),
                        total=total,
                        subjects=subjects,
                    )
                )

        return findings
