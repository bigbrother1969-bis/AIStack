from pathlib import Path

from aistack.contracts.eligibility import (
    EligibilityReport,
)

from .rules import (
    EXCLUDED_PARTS,
    EXCLUDED_PATHS,
    INCLUDED_PATHS,
    SUPPORTED_EXTENSIONS,
    matches_path,
)


class KnowledgeArtifactEligibility:
    """
    Determines whether a filesystem object is eligible
    to become a Knowledge Artifact.

    Eligibility is an allow list first: a path outside the
    governed heritage is not a candidate, whatever else is true
    of it. Exclusions then carve out what sits inside that
    perimeter but is not governed knowledge — working notes,
    generated output, transit records.
    """

    def evaluate(
        self,
        root: Path,
        path: Path,
    ) -> EligibilityReport:

        if path.suffix not in SUPPORTED_EXTENSIONS:
            return EligibilityReport(
                eligible=False,
                reason="unsupported_extension",
            )

        if any(
            part in EXCLUDED_PARTS
            for part in path.parts
        ):
            return EligibilityReport(
                eligible=False,
                reason="excluded_directory",
            )

        try:
            relative = (
                path.relative_to(root)
                .as_posix()
            )

        except ValueError:
            relative = path.as_posix()

        if not any(
            matches_path(relative, prefix)
            for prefix in INCLUDED_PATHS
        ):
            return EligibilityReport(
                eligible=False,
                reason="outside_governed_heritage",
            )

        if any(
            matches_path(relative, prefix)
            for prefix in EXCLUDED_PATHS
        ):
            return EligibilityReport(
                eligible=False,
                reason="excluded_path",
            )

        return EligibilityReport(
            eligible=True,
            reason="knowledge_artifact",
        )
