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

    The path it reports is relative to the root it was given (the
    artifact builder writes it with forward slashes). An absolute
    path names the machine and the directory the bundle happened to
    be generated in — a fact about the generation, not about the
    knowledge — and every artifact carried it as its `source` until
    `GOV-0002/OS-096`. The same heritage generated in two
    directories now carries the same sources.
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
                    path=path.relative_to(root),
                    content=content,
                    content_hash=digest,
                )
            )

        return results
