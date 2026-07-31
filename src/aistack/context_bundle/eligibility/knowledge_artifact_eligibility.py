from pathlib import Path


EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "archive",
    "reports",
    "exports",
    ".pytest_cache",
}


EXCLUDED_PATHS = {
    "context/bundles",
    "context/published",
    "inbox",
    ".pytest_cache",
}


SUPPORTED_EXTENSIONS = {
    ".md",
}


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
