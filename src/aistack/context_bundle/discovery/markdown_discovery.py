from hashlib import sha256
from pathlib import Path

from aistack.contracts.discovery import (
    DiscoveryResult,
)
from aistack.context_bundle.eligibility.knowledge_artifact_eligibility import (
    KnowledgeArtifactEligibility,
)


class MarkdownDiscovery:
    """
    Discover markdown knowledge sources.

    This component only observes files.
    It does not classify or interpret knowledge.
    """

    def __init__(self) -> None:
        self._eligibility = KnowledgeArtifactEligibility()

    def discover(
        self,
        root: Path,
    ) -> list[DiscoveryResult]:

        results: list[DiscoveryResult] = []

        for path in sorted(root.rglob("*.md")):

            report = self._eligibility.evaluate(
                root=root,
                path=path,
            )

            if not report.eligible:
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
