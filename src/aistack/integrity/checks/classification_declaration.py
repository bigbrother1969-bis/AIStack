from aistack.contracts.classification import (
    KnowledgeDomain,
    SemanticType,
)
from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.criticality import CriticalityLevel
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)
from aistack.contracts.undeclared import UNDECLARED

from aistack.context_bundle.builders.frontmatter import (
    parse_artifact_frontmatter,
)


CORE_LEVEL = CriticalityLevel.C3.name


VOCABULARIES = (
    (
        "domain",
        "domain",
        tuple(member.value for member in KnowledgeDomain),
    ),
    (
        "semantic_type",
        "semantic type",
        tuple(member.value for member in SemanticType),
    ),
    (
        "criticality",
        "criticality",
        tuple(f"C{member.value}" for member in CriticalityLevel),
    ),
)


class ClassificationDeclarationCheck(IntegrityCheck):
    """
    Observe whether artifacts are qualified, and whether their
    qualifications belong to a governed vocabulary.

    Domain, semantic type and criticality are qualifications.
    They are declared by a human, never inferred, so their
    absence is a real state of the heritage and is reported as
    such.

    Two absences are distinguished, because they call for
    different work:

    - **nothing was declared** — the artifact awaits
      qualification;
    - **something was declared that no vocabulary contains** —
      the artifact was qualified, wrongly. The pipeline reports
      it as `unknown`, so without this finding the mistake would
      be indistinguishable from silence.

    The blocking condition is neither of those. It is that **no
    artifact is declared C3**: the README bootstrap protocol
    asks an agent to acquire a minimal governed context, and
    without a core level there is nothing minimal to select.
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

        for field, label, vocabulary in VOCABULARIES:

            undeclared: list[str] = []
            invalid: list[str] = []

            for artifact in bundle.artifacts:

                if getattr(artifact, field) != UNDECLARED:
                    continue

                written = parse_artifact_frontmatter(
                    artifact.content
                ).get(field)

                if written is None or not str(written).strip():
                    undeclared.append(artifact.source)
                else:
                    invalid.append(artifact.source)

            if undeclared:
                findings.append(
                    IntegrityFinding(
                        check=self.name,
                        severity=IntegritySeverity.WARNING,
                        summary=(
                            "artifacts reach a consumer with "
                            f"no {label}"
                        ),
                        affected=len(undeclared),
                        total=total,
                        subjects=tuple(undeclared),
                    )
                )

            if invalid:
                findings.append(
                    IntegrityFinding(
                        check=self.name,
                        severity=IntegritySeverity.WARNING,
                        summary=(
                            f"artifacts declare a {label} that "
                            "no governed vocabulary contains "
                            f"({' · '.join(vocabulary)})"
                        ),
                        affected=len(invalid),
                        total=total,
                        subjects=tuple(invalid),
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
