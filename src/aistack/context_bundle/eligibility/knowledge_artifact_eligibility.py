from pathlib import Path

from aistack.contracts.eligibility import (
    EligibilityReport,
)

from .rules import (
    EXCLUDED_PARTS,
    EXCLUDED_PATHS,
    SUPPORTED_EXTENSIONS,
)


class KnowledgeArtifactEligibility:
    """
    Determines whether a filesystem object is eligible
    to become a Knowledge Artifact.
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

        if any(
            relative.startswith(prefix)
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
