from hashlib import sha256
from pathlib import Path

from aistack.contracts.discovery import DiscoveryResult


EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "archive",
    "reports",
    "exports",
}


EXCLUDED_PATHS = {
    "context/bundles",
    "context/published",
    "inbox",
}


class MarkdownDiscovery:
    """
    Discover markdown knowledge sources.

    This component only observes files.
    It does not classify or interpret knowledge.
    """

    def discover(
        self,
        root: Path,
    ) -> list[DiscoveryResult]:

        results = []

        for path in sorted(root.rglob("*.md")):

            if self._excluded(
                root,
                path,
            ):
                continue

            content = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            digest = sha256(
                content.encode("utf-8")
            ).hexdigest()

            results.append(
                DiscoveryResult(
                    path=path,
                    content=content,
                    content_hash=digest,
                )
            )

        return results


    def _excluded(
        self,
        root: Path,
        path: Path,
    ) -> bool:

        if any(
            part in EXCLUDED_PARTS
            for part in path.parts
        ):
            return True


        try:
            relative = (
                path.relative_to(root)
                .as_posix()
            )

        except ValueError:
            relative = path.as_posix()


        return any(
            relative.startswith(prefix)
            for prefix in EXCLUDED_PATHS
        )
