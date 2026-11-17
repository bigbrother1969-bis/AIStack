from aistack.contracts.context_bundle import ContextBundle
from aistack.contracts.integrity_check import IntegrityCheck
from aistack.contracts.integrity_finding import (
    IntegrityFinding,
    IntegritySeverity,
)


CONFLICT_MARKERS = (
    "<<<<<<<",
    ">>>>>>>",
)


def _has_conflict_marker(content: str) -> bool:

    return any(
        line.startswith(CONFLICT_MARKERS)
        for line in content.split("\n")
    )


def _has_unterminated_frontmatter(content: str) -> bool:

    lines = content.split("\n")

    if not lines or lines[0].strip() != "---":
        return False

    return not any(
        line.strip() == "---"
        for line in lines[1:]
    )


def _has_unbalanced_fences(content: str) -> bool:

    fences = sum(
        1
        for line in content.split("\n")
        if line.startswith("```")
    )

    return fences % 2 == 1


class StructuralIntegrityCheck(IntegrityCheck):
    """
    Observe damage that makes an artifact unparseable.

    The AIStack README carried an unresolved conflict marker
    for fourteen commits and through at least one published
    bundle. Such damage must be reported, not survived.
    """

    @property
    def name(self) -> str:
        return "structural-integrity"

    def evaluate(
        self,
        bundle: ContextBundle,
    ) -> list[IntegrityFinding]:

        total = len(bundle.artifacts)

        findings: list[IntegrityFinding] = []

        for summary, severity, predicate in (
            (
                "artifacts contain an unresolved conflict marker",
                IntegritySeverity.BLOCKING,
                _has_conflict_marker,
            ),
            (
                "artifacts open a metadata block they never close",
                IntegritySeverity.BLOCKING,
                _has_unterminated_frontmatter,
            ),
            (
                "artifacts contain an unbalanced code fence",
                IntegritySeverity.WARNING,
                _has_unbalanced_fences,
            ),
        ):

            subjects = tuple(
                artifact.source
                for artifact in bundle.artifacts
                if predicate(artifact.content)
            )

            if subjects:
                findings.append(
                    IntegrityFinding(
                        check=self.name,
                        severity=severity,
                        summary=summary,
                        affected=len(subjects),
                        total=total,
                        subjects=subjects,
                    )
                )

        return findings
