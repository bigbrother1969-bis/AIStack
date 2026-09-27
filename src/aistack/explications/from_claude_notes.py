"""
Import the project's own `claude/*.md` session notes as Explications —
`ADR-0011` § *Decision* 8's third real source. Scope decided with the
owner alongside patch 0056: only the 5 files this repository itself
versions under `claude/`, not the 73 documents the owner's separate
Claude Project holds on claude.ai — a rebuild running headless on
GIGABYTE has no path to the latter without a new export mechanism this
patch does not build (`ADR-0011` § 8's own corrected text says so).

**Subject and date come from each note's own declared frontmatter when
it has one** (`aistack.context_bundle.builders.frontmatter
.parse_artifact_frontmatter` — the same generic YAML-frontmatter-block
reader the Context Bundle's own `MarkdownArtifactBuilder` already uses,
reused directly rather than rebuilt; not that builder itself, though —
an Explication is not a discovered document, the same reasoning
`aistack.explications.store`'s own docstring already gives for not
reusing `ArtifactBuilder`). Measured 2026-09-27: 4 of the 5 real files
declare `artifact.id`/`artifact.updated` (and `artifact.created`); the
subject is that `id`, the note's own real date is `updated`, falling
back to `created`. One real file, `PLAN-VS2-2.4-PROTOCOL-2026-09-25.md`,
declares no frontmatter at all — its subject falls back to the
filename's own stem, and its date to the first `YYYY-MM-DD` found in
that same filename. A note yielding neither a subject nor a date this
way is skipped and counted, not guessed at (`ARC-P-006`).

**The idempotency signal is a content hash, not an instant.** Unlike
`explain` answers or `pra_tests.yml`'s own dated comments, a `claude/`
note carries no separate "this is when the fact changed" marker
distinct from the file's own single edit history — the file *is* the
note, and an edited note is a real correction deserving its own new
Explication version, exactly as `ADR-0011` § 7 already describes.
`metadata["source_content_hash"]` (sha256 of the file's raw text) is
what this module compares against `read_explication_history` before
recording — re-running it after a note's text changes records a new
version; after no change, records nothing.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from aistack.context_bundle.builders.frontmatter import (
    declared_value,
    parse_artifact_frontmatter,
)
from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED, is_declared
from aistack.explications.store import (
    DEFAULT_OUTPUT_DIR,
    read_explication_history,
    record_explication,
)

DEFAULT_CLAUDE_NOTES_DIR = Path(__file__).resolve().parents[3] / "claude"

_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class ClaudeNotesImportSummary:
    """What one `import_claude_notes` run actually did."""

    notes_seen: int
    notes_skipped: int
    explications_recorded: int
    explications_already_imported: int


def _parse_date(text: str) -> datetime | None:
    match = _DATE_PATTERN.search(text)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(0), "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def _subject_and_date(path: Path, text: str) -> tuple[str | None, datetime | None]:
    """
    A note's own subject and date: its declared `artifact.id` and
    `artifact.updated` (falling back to `artifact.created`) when it
    has real frontmatter, or the filename's own stem and embedded
    date when it does not. Never a guess beyond what the file itself
    or its name actually states.
    """

    declared = parse_artifact_frontmatter(text)

    if declared:
        declared_id = declared_value(declared, "id")
        if is_declared(declared_id):
            date_text = declared.get("updated") or declared.get("created")
            date = _parse_date(str(date_text)) if date_text else None
            return declared_id, date

    return path.stem, _parse_date(path.name)


def import_claude_notes(
    claude_notes_dir: Path = DEFAULT_CLAUDE_NOTES_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> ClaudeNotesImportSummary:
    """
    Import every `*.md` file directly under `claude_notes_dir` as a
    `Proposed` `KnowledgeArtifact` (`ADR-0011` § 7-8), one Explication
    per note (not recursive — the real corpus is flat today, and a
    future subdirectory is a real shape to measure when one exists,
    not one to assume now).
    """

    notes_seen = 0
    notes_skipped = 0
    explications_recorded = 0
    explications_already_imported = 0

    for path in sorted(claude_notes_dir.glob("*.md")):
        notes_seen += 1
        text = path.read_text(encoding="utf-8")
        subject, date = _subject_and_date(path, text)

        if subject is None or date is None:
            notes_skipped += 1
            continue

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

        already_imported = {
            artifact.metadata.get("source_content_hash")
            for artifact in read_explication_history(subject, output_dir)
            if artifact.metadata.get("source_stream") == "claude-notes"
        }

        if content_hash in already_imported:
            explications_already_imported += 1
            continue

        artifact = KnowledgeArtifact(
            id=subject,
            title=f"Explication : {subject}",
            declared_type="Explication",
            domain=UNDECLARED,
            semantic_type=UNDECLARED,
            criticality=UNDECLARED,
            owner=UNDECLARED,
            source=f"file:claude/{path.name}",
            created_at=date,
            updated_at=date,
            confidence="Proposed",
            status=UNDECLARED,
            content=text,
            metadata={
                "source_stream": "claude-notes",
                "source_content_hash": content_hash,
                "source_path": f"claude/{path.name}",
                "explication_status": "Proposed",
            },
        )
        record_explication(artifact, output_dir=output_dir)
        explications_recorded += 1

    return ClaudeNotesImportSummary(
        notes_seen=notes_seen,
        notes_skipped=notes_skipped,
        explications_recorded=explications_recorded,
        explications_already_imported=explications_already_imported,
    )
