from pathlib import Path

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

    def is_eligible(
        self,
        root: Path,
        path: Path,
    ) -> bool:

        if path.suffix not in SUPPORTED_EXTENSIONS:
            return False

        if any(
            part in EXCLUDED_PARTS
            for part in path.parts
        ):
            return False

        try:
            relative = (
                path.relative_to(root)
                .as_posix()
            )

        except ValueError:
            relative = path.as_posix()

        return not any(
            relative.startswith(prefix)
            for prefix in EXCLUDED_PATHS
        )
