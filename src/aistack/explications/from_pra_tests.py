"""
Import the dated comment blocks of `pra_tests.yml` as Explications
(`ADR-0011` § 8).

A block is a run of `#` comment lines starting with a bold lede, e.g.
"**`arrstack` corrected to `success`, same day (2026-09-26).**". The
subject is the first backtick-quoted token in the lede and the date the
first `YYYY-MM-DD`. A block without either is skipped and counted in
`blocks_skipped`, never guessed. Lines before the first lede are the
file header and are not imported.

Blocks for the same subject and date are merged, in file order, into
one Explication: the source has day precision only.

Idempotent by (subject, date) via `metadata["source_instant"]`; a block
whose text changes for an already-imported date is not re-imported.
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
    """The file's leading run of `#` comment lines, markers stripped."""

    lines: list[str] = []
    for line in text.splitlines():
        if not line.startswith("#"):
            break
        lines.append(_strip_comment_marker(line))
    return lines


def _split_into_blocks(header_lines: list[str]) -> list[list[str]]:
    """
    Group comment lines into blocks, each starting at a line beginning
    with `**`. Lines before the first one and blank lines are dropped.
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
    Return a block's subject (first backtick token in the lede,
    lowercased), date (first `YYYY-MM-DD` in the lede) and text without
    the bold markers. Subject or date is `None` when the lede lacks it.
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
    Record one `Proposed` `KnowledgeArtifact` per (subject, date) pair
    in `pra_tests_path` not already imported (`ADR-0011` § 7-8).
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
