from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Provenance:
    """
    Governed provenance contract — J3, Time Foundation
    (`claude/PLAN-J3-TIME-FOUNDATION-2026-09-10.md`).

    **Replaces `aistack.kernel.knowledge.artifact.provenance
    .KnowledgeProvenance`, rather than sitting beside it.** That
    type (`source: str`, `provider: str`) was never wired to a real
    persistence path — `kernel/knowledge/repository/` holds only an
    in-memory repository, no file-backed one — so nothing in this
    heritage has ever actually recorded a `KnowledgeProvenance` with
    two independently-meaningful `source`/`provider` values; its only
    two call sites are its own construction test and the
    `KnowledgeArtifact` it is embedded in, neither a real producer.
    This contract keeps one field, `origin`, for what every real
    producer this session found (Docker/Compose providers,
    `decision_history`, `ExecutionTrace`'s own `request`/`resolution`)
    already has exactly one of: the identity of the component that
    produced the snapshotted content.

    `causality` is new, not a rename of anything `KnowledgeProvenance`
    had: the identifier of the request or task that *caused*
    production, when one exists. `ExecutionTrace.request.request_id`
    is already this, informally — carried through `ExecutionTrace`'s
    own `request` field rather than a governed `Provenance`. Optional
    because Observation History's providers (`docker_discover`,
    `compose_catalog`) are not triggered by any `Request` today — they
    are plain CLI entry points — so a snapshot of their output has an
    `origin` but no `causality` to name.

    The second, independent `KnowledgeArtifact`/`KnowledgeProvenance`
    pair this contract supersedes is not deleted by this patch — its
    disposition (merge, rewrite, or removal) is Knowledge Heritage
    History's concern, not Time Foundation's, and is tracked as its
    own open `GOV-0002` entry rather than folded into J3's scope.

    **Note added 2026-09-18 — the paragraph above no longer holds.**
    `GOV-0002/OS-058` resolved: the second `KnowledgeArtifact` and
    its `KnowledgeProvenance` were removed. `KnowledgeLifecycle` and
    `KnowledgeScore`, the two fields of that pair the owner chose to
    keep, were merged into the production `KnowledgeArtifact`
    (`aistack.contracts.artifact`) — `KnowledgeProvenance` itself was
    not: this contract, `Provenance`, already supersedes it, exactly
    as the paragraph above always said.
    """

    origin: str
    causality: str | None = None
