"""
What the health cockpit said at its last render, for the vigil
(`aistack.cli.vigil`) to compare with the one before: the score, the
technical debt, and every finding, by a stable key.

Written by `aistack.cli.health_render` beside `health.html`, as
`health-state.json`; replaced at every render.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aistack.health.cockpit import HealthCockpit

FILE = "health-state.json"


@dataclass(frozen=True)
class SnapshotFinding:
    key: str
    domain: str
    subject: str
    text: str
    # (catalog key, params) of the interpretation, to say it in the
    # reader's language; empty when the evaluator has none.
    message: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = ()


@dataclass(frozen=True)
class Snapshot:
    at: str
    score: int | None
    debt: int | None
    findings: tuple[SnapshotFinding, ...] = field(default_factory=tuple)


def finding_key(domain: str, subject: str, kind: str) -> str:
    """Stable across renders; a finding that changes kind (a PRA test
    from stale to failed) is a new finding."""

    return f"{domain}::{subject}::{kind}"


def take(cockpit: HealthCockpit, score: int | None, debt: int | None, now: datetime | None = None) -> Snapshot:
    findings = []
    for domain in cockpit.domains:
        for finding in domain.findings:
            parts = finding.message.interpretation if finding.message is not None else ()
            kind = parts[0].key if parts else finding.signature
            findings.append(
                SnapshotFinding(
                    key=finding_key(domain.name, finding.subject, kind),
                    domain=domain.name,
                    subject=finding.subject,
                    text=finding.interpretation,
                    message=tuple((p.key, p.params) for p in parts),
                )
            )
    moment = (now or datetime.now(timezone.utc)).isoformat(timespec="seconds")
    return Snapshot(moment, score, debt, tuple(findings))


def write(snapshot: Snapshot, generated_dir: Path) -> Path:
    path = generated_dir / FILE
    data: dict[str, Any] = {
        "at": snapshot.at,
        "score": snapshot.score,
        "debt": snapshot.debt,
        "findings": [
            {
                "key": f.key,
                "domain": f.domain,
                "subject": f.subject,
                "text": f.text,
                "message": [[key, [list(p) for p in params]] for key, params in f.message],
            }
            for f in snapshot.findings
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def read(generated_dir: Path) -> Snapshot | None:
    try:
        data = json.loads((generated_dir / FILE).read_text(encoding="utf-8"))
        return Snapshot(
            at=str(data["at"]),
            score=data.get("score"),
            debt=data.get("debt"),
            findings=tuple(
                SnapshotFinding(
                    key=str(f["key"]),
                    domain=str(f["domain"]),
                    subject=str(f["subject"]),
                    text=str(f.get("text") or ""),
                    message=tuple(
                        (str(key), tuple((str(a), str(b)) for a, b in params))
                        for key, params in f.get("message") or []
                    ),
                )
                for f in data.get("findings") or []
            ),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None
