"""
A governed change's why, recorded as its explication (`ADR-0019` § 2):
once the dock has executed a proposal, the reason its author wrote is
recorded in the Time Machine for each container it changed — under the
same stable subject the image-digest collector observes it by
(`<compose project>/<compose service>`), so the why sits beside the
observations the change produced.

Attributed to the person who wrote it; the administrator who validated
it, when another, is its second author (`ADR-0015` § 5). Written by a
person and validated, so `Declared` and `Validated`; the outcome and
the proposal are said in the text and kept in `metadata`
(`dock_proposal`), which the provenance graph follows to tie the
change's activity to its explication.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.dock import proposals as store
from aistack.explications.human import DECLARED, VALIDATED, person_source
from aistack.explications.store import record_explication

SOURCE_STREAM = "dock"

OUTCOMES = {
    store.APPLIED: "appliquée",
    store.ROLLED_BACK: "revenue en arrière (les vérifications ont échoué, l'image précédente tourne de nouveau)",
    store.FAILED: "échouée",
}


def change_subject(change: store.ImageChange) -> str:
    """The stable subject the digest collector names the container by."""

    if change.compose_project and change.compose_service:
        return f"{change.compose_project}/{change.compose_service}"
    return change.container


def record_change_explication(generated_dir: Path, proposal: store.Proposal, now: datetime) -> list[str]:
    """Record the why of an executed proposal; returns the subjects."""

    outcome = OUTCOMES.get(proposal.status, proposal.status)
    last = proposal.history[-1]["detail"] if proposal.history else ""
    subjects = []
    for change in proposal.changes:
        subject = change_subject(change)
        content = "\n\n".join(part for part in (
            proposal.why,
            f"Dock, proposition {proposal.id} : {change.image} "
            f"{change.from_digest[:19]}… → {change.to_digest[:19]}… — {outcome}."
            + (f" {last}" if last and proposal.status != store.APPLIED else ""),
        ) if part)
        metadata: dict[str, object] = {
            "source_stream": SOURCE_STREAM,
            "explication_status": VALIDATED,
            "dock_proposal": proposal.id,
            "outcome": proposal.status,
        }
        if proposal.decided_by and proposal.decided_by != proposal.proposed_by:
            metadata["validated_by"] = person_source(proposal.decided_by)
        record_explication(
            KnowledgeArtifact(
                id=subject,
                title=f"Explication : {subject}",
                declared_type="Explication",
                domain=UNDECLARED,
                semantic_type=UNDECLARED,
                criticality=UNDECLARED,
                owner=UNDECLARED,
                source=person_source(proposal.proposed_by),
                created_at=now,
                updated_at=now,
                confidence=DECLARED,
                status=UNDECLARED,
                content=content,
                metadata=metadata,
            ),
            output_dir=generated_dir / "explications",
        )
        subjects.append(subject)
    return subjects
