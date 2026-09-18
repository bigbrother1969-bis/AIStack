from __future__ import annotations

from enum import Enum


class KnowledgeLifecycle(str, Enum):
    """
    Lifecycle state of a governed knowledge artifact.

    Moved here from `aistack.kernel.knowledge.artifact.lifecycle`
    (`GOV-0002/OS-058`, resolved 2026-09-18): that module existed
    only to serve a second, unwired `KnowledgeArtifact` definition,
    never called from any CLI or generator. This enum is the part
    of it the owner chose to keep, merged into the production
    `KnowledgeArtifact` (`aistack.contracts.artifact`) rather than
    left behind with the rest.

    Named `knowledge_lifecycle`, not `lifecycle` — that name was
    already taken in this package by `LifecycleDeclaration`/
    `LifecycleRegister` (`OPS-0001`, container run expectations), an
    unrelated concept. Colliding the two files was the first draft
    of this patch and was caught before it shipped.
    """

    DISCOVERED = "discovered"
    VALIDATED = "validated"
    ACTIVE = "active"
    ARCHIVED = "archived"
