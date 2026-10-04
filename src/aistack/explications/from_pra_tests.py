"""
Import `pra_tests.yml`'s own dated comments as Explications —
`ADR-0011` § *Decision* 8's second real source, chosen next (the
owner's own decision, 2026-09-27) because its whole corpus is a
handful of hand-written prose blocks, each already naming its own
subject and date in plain text: the least modelling to invent, unlike
669 commits (whose own "subject" has no obvious answer) or the
`claude/` notes (whose own corpus scope — 5 files in this repository
versus the 73 the owner's Claude Project separately holds — needed
its own decision first).

**The real shape, measured before writing any parser.** The file's
own dated facts live as free prose inside `#` comments, each block
opening with a bold Markdown lede that names a subject in backticks
and a date in parentheses or after a comma — e.g. "**`arrstack`
corrected to `success`, same day (2026-09-26).**" — followed by
several more comment lines of plain narrative. A block is recognised
by that opening `**`; nothing before the first one (the file's own
header, "Declared 2026-09-23 by the owner...") is one, and is not
imported — it is the file's own provenance statement about itself,
not a dated fact about a subject.

**A block with no backtick-quoted subject in its lede is skipped, not
guessed.** One real block in this file today — "**Vikunja gap closed,
same day (2026-09-26).**" — names its subject only in prose, not in
backticks. Inventing a "first word of the lede" rule to catch it would
be exactly the guessed inference `ARC-P-006` forbids for a corpus this
small; `blocks_skipped` in the summary reports the real count instead,
and the owner can wrap a future lede's subject in backticks (as every
other block already does) to make it importable.

**Same-day blocks for the same subject are merged into one
Explication, not recorded as two.** `pra_tests.yml`'s own comments
carry day-granularity dates only — nothing in the source distinguishes
"first thing that morning" from "an hour later" — so recording
`arrstack`'s "recorded as failed" and "corrected to success, same day"
as two separately-timestamped Explication versions would assert a
precision the source does not actually have. Worse, it would collide
with a real defect this module's own testing found in
`aistack.history.query.available_instants`: two writes to the same
subject's history landing in the same wall-clock second collapse to
one queryable instant (its own docstring says so plainly), so the
earlier of two same-second writes would silently stop being visible to
`read_explication_history` and to the graph projection — a real data
loss this module avoids entirely by writing at most once per
(subject, date) pair, concatenating same-day blocks' own text in file
order (so "recorded as failed" still reads before "corrected to
success" inside the one Explication) rather than by reaching into
`write_artifact_with_history` or `available_instants` to fix a
timestamp-precision problem this source does not have the data to need.

**Idempotent the same way `from_ai_reasoning` already is**: every
recorded Explication's `metadata["source_instant"]` is the group's own
date string; before writing, this module reads every Explication
already recorded for that subject and skips a (subject, date) pair
already present — the files on disk are the ledger, no second one.
Re-importing after the file's prose changes for an already-recorded
date does not update it — a real, documented limitation of "by date",
not "by content", the same choice `from_ai_reasoning` already made for
"by instant".
"""

from __future__ import annotations

from aistack.config import configured

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.explications.store import (
    DEFAULT_OUTPUT_DIR,
    read_explication_history,
    record_explication,
)

DEFAULT_PRA_TESTS_PATH = (
    configured(Path(__file__).resolve().parents[1] / "pra" / "definitions" / "pra_tests.yml")
)

_LEDE_PATTERN = re.compile(r"^\*\*(?P<lede>.+?)\*\*\s*(?P<rest>.*)$")
_SUBJECT_PATTERN = re.compile(r"`([^`]+)`")
_DATE_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}")


@dataclass(frozen=True)
class PraTestsImportSummary:
    """What one `import_pra_tests_comments` run actually did."""

    blocks_seen: int
    blocks_skipped: int
    subjects_seen: int
    explications_recorded: int
    explications_already_imported: int


def _strip_comment_marker(line: str) -> str:
    text = line[1:]
    if text.startswith(" "):
        text = text[1:]
    return text


def _comment_header_lines(text: str) -> list[str]:
    """
    The file's leading run of `#` comment lines, stopping at the
    first real (non-comment) line — `pra_tests.yml`'s own blank line
    before `max_age_days:` today, but this stops at whichever line
    ends the comment run, not a hardcoded line number.
    """

    lines: list[str] = []
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        lines.append(_strip_comment_marker(line))
    return lines


def _split_into_blocks(header_lines: list[str]) -> list[list[str]]:
    """
    Group the header's own comment lines into dated blocks, each
    starting at a line beginning with `**` (the bold lede). Lines
    before the first such marker (the file's own provenance header)
    form no block at all. A blank comment line is a separator, kept
    out of every block's own text.
    """

    blocks: list[list[str]] = []
    current: list[str] | None = None

    for text in header_lines:
        if text.startswith("**"):
            if current is not None:
                blocks.append(current)
            current = [text]
        elif current is not None and text != "":
            current.append(text)

    if current is not None:
        blocks.append(current)

    return blocks


def _parse_block(block_lines: list[str]) -> tuple[str | None, str | None, str]:
    """
    A block's own subject (the first backtick-quoted token in its
    lede, lowercased), date (the first `YYYY-MM-DD` in its lede), and
    full text (the block's lines rejoined, its bold markers dropped).
    Either of the first two is `None` when the lede does not name one
    this way — the caller skips those rather than guessing.
    """

    block_text = " ".join(block_lines)
    match = _LEDE_PATTERN.match(block_text)
    lede = match.group("lede") if match else block_text

    subject_match = _SUBJECT_PATTERN.search(lede)
    subject = subject_match.group(1).strip().lower() if subject_match else None

    date_match = _DATE_PATTERN.search(lede)
    date = date_match.group(0) if date_match else None

    content = block_text.replace("**", "", 2)

    return subject, date, content


def import_pra_tests_comments(
    pra_tests_path: Path = DEFAULT_PRA_TESTS_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> PraTestsImportSummary:
    """
    Parse `pra_tests_path`'s own dated comment blocks and record one
    `Proposed` `KnowledgeArtifact` per (subject, date) pair not already
    imported (`ADR-0011` § 7-8).
    """

    text = pra_tests_path.read_text(encoding="utf-8")
    blocks = _split_into_blocks(_comment_header_lines(text))

    blocks_seen = len(blocks)
    blocks_skipped = 0

    groups: dict[tuple[str, str], list[str]] = {}
    group_order: list[tuple[str, str]] = []

    for block_lines in blocks:
        subject, date, content = _parse_block(block_lines)
        if subject is None or date is None:
            blocks_skipped += 1
            continue

        key = (subject, date)
        if key not in groups:
            groups[key] = []
            group_order.append(key)
        groups[key].append(content)

    subjects_seen = len({subject for subject, _ in group_order})
    explications_recorded = 0
    explications_already_imported = 0

    for subject, date in group_order:
        already_imported = {
            artifact.metadata.get("source_instant")
            for artifact in read_explication_history(subject, output_dir)
            if artifact.metadata.get("source_stream") == "pra-tests"
        }

        if date in already_imported:
            explications_already_imported += 1
            continue

        created_at = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)

        artifact = KnowledgeArtifact(
            id=subject,
            title=f"Explication : {subject}",
            declared_type="Explication",
            domain=UNDECLARED,
            semantic_type=UNDECLARED,
            criticality=UNDECLARED,
            owner=UNDECLARED,
            source="file:pra_tests.yml",
            created_at=created_at,
            updated_at=created_at,
            confidence="Proposed",
            status=UNDECLARED,
            content="\n\n".join(groups[(subject, date)]),
            metadata={
                "source_stream": "pra-tests",
                "source_instant": date,
                "explication_status": "Proposed",
            },
        )
        record_explication(artifact, output_dir=output_dir)
        explications_recorded += 1

    return PraTestsImportSummary(
        blocks_seen=blocks_seen,
        blocks_skipped=blocks_skipped,
        subjects_seen=subjects_seen,
        explications_recorded=explications_recorded,
        explications_already_imported=explications_already_imported,
    )
