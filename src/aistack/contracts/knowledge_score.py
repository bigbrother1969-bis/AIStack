from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KnowledgeScore:
    """
    Trust evaluation of a knowledge artifact.

    Moved here from `aistack.kernel.knowledge.artifact.score`
    (`GOV-0002/OS-058`, resolved 2026-09-18): that module existed
    only to serve a second, unwired `KnowledgeArtifact` definition,
    never called from any CLI or generator. This dataclass is the
    part of it the owner chose to keep, merged into the production
    `KnowledgeArtifact` (`aistack.contracts.artifact`) rather than
    left behind with the rest.
    """

    confidence: float
