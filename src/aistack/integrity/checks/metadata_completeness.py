from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)

from aistack.context_bundle.builders.frontmatter import (
    parse_artifact_frontmatter,
)


REQUIRED_FIELDS = (
    "id",
    "title",
    "type",
    "version",
    "status",
    "owner",
)


class MetadataCompletenessCheck(IntegrityCheck):
    """
    FDN-0003 Article 3 requires every governed element to
    carry identity, ownership and lifecycle.

    This check observes what each artifact declares about
    itself, field by field.
    """

    @property
    def name(self) -> str:
        return "metadata-completeness"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        total = len(bundle.artifacts)

        undeclared: list[str] = []
        partial: list[str] = []

        for artifact in bundle.artifacts:

            declared = parse_artifact_frontmatter(
                artifact.content
            )

            if not declared:
                undeclared.append(artifact.source)
                continue

            missing = [
                field
                for field in REQUIRED_FIELDS
                if field not in declared
            ]

            if missing:
                partial.append(artifact.source)

        findings: list[IntegrityFinding] = []

        if undeclared:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.WARNING,
                    summary=(
                        "artifacts declare no metadata block at all"
                    ),
                    affected=len(undeclared),
                    total=total,
                    subjects=tuple(undeclared),
                )
            )

        if partial:
            findings.append(
                IntegrityFinding(
                    check=self.name,
                    severity=IntegritySeverity.WARNING,
                    summary=(
                        "artifacts declare an incomplete metadata block"
                    ),
                    affected=len(partial),
                    total=total,
                    subjects=tuple(partial),
                )
            )

        return findings
