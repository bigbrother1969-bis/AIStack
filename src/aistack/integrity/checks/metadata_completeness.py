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
    "semantic_type",
    "domain",
    "criticality",
    "version",
    "status",
    "confidence",
    "owner",
    "created",
    "updated",
)


class MetadataCompletenessCheck(IntegrityCheck):
    """
    Observe whether each artifact wrote the twelve fields
    STD-0100 v2.0 makes mandatory.

    This check answers one question only: **was the field
    written?** Whether what was written belongs to a governed
    vocabulary is a different question, answered by
    `classification-declaration`. Keeping them apart matters:
    a field can be present and hold a value no vocabulary
    contains, and a check that conflated the two would report
    that artifact as complete.

    This check reads the **source**: the frontmatter the artifact
    wrote. `classification-declaration` and `knowledge-state`
    read the **projection**: what a consumer holding only the
    bundle actually receives. The two vantage points are kept
    apart on purpose — a value written here and missing there
    means the pipeline is destroying knowledge in transit, which
    has happened three times in this repository.

    The fields are read from the single `artifact:` mapping the
    standard defines. An artifact declaring `created` and
    `updated` in a separate `lifecycle:` block is reported as
    not declaring them — which is accurate: the standard
    specifies one block, and a consumer reading the governed
    structure will not find them.
    """

    @property
    def name(self) -> str:
        return "metadata-completeness"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        total = len(bundle.artifacts)

        if not total:
            return []

        undeclared: list[str] = []
        missing_by_field: dict[str, list[str]] = {
            field: [] for field in REQUIRED_FIELDS
        }

        for artifact in bundle.artifacts:

            declared = parse_artifact_frontmatter(
                artifact.content
            )

            if not declared:
                undeclared.append(artifact.source)
                continue

            for field in REQUIRED_FIELDS:
                if field not in declared:
                    missing_by_field[field].append(
                        artifact.source
                    )

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

        for field in REQUIRED_FIELDS:

            subjects = missing_by_field[field]

            if subjects:
                findings.append(
                    IntegrityFinding(
                        check=self.name,
                        severity=IntegritySeverity.WARNING,
                        summary=(
                            "artifacts have a metadata block "
                            f"but do not write {field} in it"
                        ),
                        affected=len(subjects),
                        total=total,
                        subjects=tuple(subjects),
                    )
                )

        return findings
