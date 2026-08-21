from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.criticality import CriticalityLevel
from aistack.contracts.undeclared import UNDECLARED
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


CORE_LEVEL = CriticalityLevel.C3.name


class ClassificationDeclarationCheck(IntegrityCheck):
    """
    Observe whether artifacts are qualified.

    Domain, semantic type and criticality are qualifications.
    They are declared by a human, never inferred, so their
    absence is a real state of the heritage and is reported
    as such.

    The blocking condition is not that criticality is uniform
    — that was a proxy. It is that **no artifact is declared
    C3**: the README bootstrap protocol asks an agent to
    acquire a minimal governed context, and without a core
    level there is nothing minimal to select.
    """

    @property
    def name(self) -> str:
        return "classification-declaration"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        total = len(bundle.artifacts)

        if not total:
            return []

        findings: list[IntegrityFinding] = []

        for field, label in (
            ("domain", "domain"),
            ("semantic_type", "semantic type"),
            ("criticality", "criticality"),
        ):

            subjects = tuple(
                artifact.source
                for artifact in bundle.artifacts
                if getattr(artifact, field) == UNDECLARED
            )

            if subjects:
                findings.append(
                    IntegrityFinding(
                        check=self.name,
                        severity=IntegritySeverity.WARNING,
                        summary=(
                            f"artifacts declare no {label}"
                        ),
                        affected=len(subjects),
                        total=total,
                        subjects=subjects,
                    )
                )

        core = tuple(
            artifact.source
            for artifact in bundle.artifacts
            if artifact.criticality == CORE_LEVEL
        )

        if not core:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.BLOCKING,
                    summary=(
                        f"no artifact is declared {CORE_LEVEL}; "
                        "a minimal governed context cannot be "
                        "selected"
                    ),
                    affected=total,
                    total=total,
                )
            )

        return findings
