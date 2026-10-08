"""
Proposals (`ADR-0019` § 2–3): one governed change, from its why to its
outcome, kept as one JSON file under the data directory
(`dock/proposals/<id>.json`). Every transition is appended to the
proposal's own history, never rewritten.

States: `proposed` → `validated` | `rejected`; the dock executor takes
a `validated` one → `running` → `applied` | `failed` | `rolled_back`.
In production a proposal is validated by another administrator than
the one who proposed it; in the development phase one may do both
(`ADR-0016`).
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROPOSED = "proposed"
VALIDATED = "validated"
REJECTED = "rejected"
RUNNING = "running"
APPLIED = "applied"
FAILED = "failed"
ROLLED_BACK = "rolled_back"
STATES = (PROPOSED, VALIDATED, REJECTED, RUNNING, APPLIED, FAILED, ROLLED_BACK)
OPEN = (PROPOSED, VALIDATED, RUNNING)

MIN_WHY = 10


class ProposalRefused(ValueError):
    """A transition the rules do not allow: `key` names the reason in
    the `dock.refused` catalog, `values` fill it."""

    def __init__(self, key: str, **values: str) -> None:
        super().__init__(key)
        self.key = f"dock.refused.{key}"
        self.values = values


@dataclass(frozen=True)
class ImageChange:
    container: str
    image: str
    from_digest: str
    to_digest: str
    from_image_id: str = ""
    compose_project: str = ""
    compose_service: str = ""
    compose_dir: str = ""
    # Compose's own label, comma-separated: the files the dock recreates
    # the container with (`ADR-0019` § 5).
    compose_files: str = ""


@dataclass
class Proposal:
    id: str
    service: str
    changes: list[ImageChange]
    why: str
    proposed_by: str
    proposed_at: str
    status: str = PROPOSED
    decided_by: str = ""
    decided_at: str = ""
    history: list[dict[str, str]] = field(default_factory=list)
    # What the dock executor did, one entry per operation (`ADR-0019`
    # § 4–6): name, status, start, seconds, detail.
    operations: list[dict[str, Any]] = field(default_factory=list)

    def note(self, event: str, by: str, detail: str = "", at: str = "") -> None:
        self.history.append({"at": at or _now(), "by": by, "event": event, "detail": detail})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def proposals_dir(generated_dir: Path) -> Path:
    return generated_dir / "dock" / "proposals"


def save(generated_dir: Path, proposal: Proposal) -> Path:
    directory = proposals_dir(generated_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / f"{proposal.id}.json"
    partial = target.with_suffix(".json.partial")
    partial.write_text(json.dumps(asdict(proposal), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(partial, target)
    return target


def _from_dict(data: dict[str, Any]) -> Proposal:
    changes = [ImageChange(**change) for change in data.get("changes") or []]
    return Proposal(**{**data, "changes": changes})


def load(generated_dir: Path, proposal_id: str) -> Proposal:
    if not proposal_id or "/" in proposal_id or proposal_id.startswith("."):
        raise ProposalRefused("unknown")
    path = proposals_dir(generated_dir) / f"{proposal_id}.json"
    if not path.is_file():
        raise ProposalRefused("unknown")
    return _from_dict(json.loads(path.read_text(encoding="utf-8")))


def all_proposals(generated_dir: Path) -> list[Proposal]:
    directory = proposals_dir(generated_dir)
    found = []
    for path in sorted(directory.glob("*.json"), reverse=True) if directory.is_dir() else []:
        try:
            found.append(_from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError, TypeError):
            continue
    return found


def propose(
    generated_dir: Path,
    service: str,
    changes: list[ImageChange],
    why: str,
    by: str,
    *,
    now: datetime | None = None,
) -> Proposal:
    why = why.strip()
    if len(why) < MIN_WHY:
        raise ProposalRefused("why", count=str(MIN_WHY))
    if not changes:
        raise ProposalRefused("nothing")
    if any(p.service == service and p.status in OPEN for p in all_proposals(generated_dir)):
        raise ProposalRefused("open", service=service)
    moment = now or datetime.now(timezone.utc)
    proposal = Proposal(
        id=f"{service}-{moment:%Y%m%d-%H%M%S}", service=service, changes=changes, why=why,
        proposed_by=by, proposed_at=moment.isoformat(timespec="seconds"),
    )
    proposal.note("proposed", by, why, proposal.proposed_at)
    save(generated_dir, proposal)
    return proposal


def validate(generated_dir: Path, proposal_id: str, by: str, *, development: bool) -> Proposal:
    proposal = load(generated_dir, proposal_id)
    if proposal.status != PROPOSED:
        raise ProposalRefused("not_proposed", status=proposal.status)
    if not development and by == proposal.proposed_by:
        raise ProposalRefused("same_person")
    proposal.status, proposal.decided_by, proposal.decided_at = VALIDATED, by, _now()
    proposal.note("validated", by, at=proposal.decided_at)
    save(generated_dir, proposal)
    return proposal


def reject(generated_dir: Path, proposal_id: str, by: str, reason: str = "") -> Proposal:
    proposal = load(generated_dir, proposal_id)
    if proposal.status not in (PROPOSED, VALIDATED):
        raise ProposalRefused("closed", status=proposal.status)
    proposal.status, proposal.decided_by, proposal.decided_at = REJECTED, by, _now()
    proposal.note("rejected", by, reason.strip(), proposal.decided_at)
    save(generated_dir, proposal)
    return proposal
