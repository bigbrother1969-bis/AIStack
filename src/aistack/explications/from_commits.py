"""
Import this repository's own commit history as Explications —
`ADR-0011` § *Decision* 8's fourth and last real source, imported
last (the owner's own decision, 2026-09-27) because, unlike
`pra_tests.yml`'s dated comments or the `claude/` notes' frontmatter,
a commit's own "subject" has no single, uniform answer — real
modelling work, done here only after measuring the real corpus rather
than guessing at its shape.

**Measured before writing any parser**, against this repository's own
695 real commits: only 240 (35%) follow the `type(scope): message`
convention (`feat(explications): ...`, `docs(governance): ...`) that
names a real architectural subject in its own first line; 149 (21%,
overlapping) instead reference a governance document id
(`OS-071`, `ADR-0011`...) with no scope at all; 318 (46%) have neither
— free prose, or a bare `type: message` with no named subject. The
owner chose, via `AskUserQuestion`, the narrowest of three measured
options: **only the 240 commits with a real conventional scope are
imported, the scope itself is the subject, and everything else is
skipped and counted** — not guessed at, the same choice this module's
own sibling `from_pra_tests` already made for the one real comment
block (`Vikunja`) whose lede names no backtick subject. A governance
document id referenced inside a scoped or unscoped message stays in
the Explication's own content, never promoted to the subject: an
architecture component (`kernel`, `console`, `explications`) and a
governance register entry (`OS-071`) are not the same kind of thing,
and conflating them under one field would misrepresent both.

**No pacing any more (1.9).** Two writes to the same subject in the
same wall-clock second used to read back as one — the history reader
kept the last write of each second — so this importer waited out a
second between two commits of one scope (up to three minutes on the
240-commit corpus). Explications are now read version by version
(`aistack.history.every_version`), each file its own version even
within one second, so the import writes as fast as it can.

**Idempotent by commit sha, not by instant or content hash.** A
commit is already immutable and already uniquely identified — no
content hash or recorded instant is needed to tell "already imported"
from "new": `metadata["source_commit_sha"]` (the commit's own full
40-character sha) is what this module compares against
`read_explication_history` before writing. Oldest-first
(`git log --reverse`), so a subject's own recorded versions replay in
the same order its real commits happened in — `created_at`/
`updated_at` carry the commit's own author date (`%aI`), the same
"real historical time as the fact, not import time" honesty
`ADR-0011` § 7 already describes for a correction.

**`source` names the commit itself, not its author.** The three
existing importers each name their own source document
(`"file:pra_tests.yml"`, `f"file:claude/{name}"`) or the model that
produced the content (`"model:{model}"`) — never a human identity.
A commit's authors are not uniform strings across this repository's
own history (`Fabrice`, `Fabrice Persiaut`, `fabrice.persiaut`,
`Claude`, `Claude Sonnet 5`, among others — measured, not assumed) and
folding them into one `prov:Agent` per spelling would fragment a
single real actor across several graph nodes. `f"git:{sha}"` keeps
the same "names the origin artifact" convention every other importer
already uses, sidestepping that fragmentation entirely; the commit's
real author/committer identity stays readable in the Explication's own
`content` (the full commit message), never lost, just not promoted to
`prov:wasAttributedTo`.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from aistack.contracts.artifact import KnowledgeArtifact
from aistack.contracts.undeclared import UNDECLARED
from aistack.explications.store import (
    DEFAULT_OUTPUT_DIR,
    read_explication_history,
    record_explication,
)

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[3]

_SCOPE_PATTERN = re.compile(r"^[a-z]+\(([^)]+)\):")

# `git log`'s own field/record separators — ASCII Unit Separator and
# End-of-Text, neither of which any real commit message in this
# repository has ever contained (measured), so a message's own text
# can never be mistaken for a field boundary.
_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x03"


@dataclass(frozen=True)
class CommitsImportSummary:
    """What one `import_commits` run actually did."""

    commits_seen: int
    commits_skipped: int
    subjects_seen: int
    explications_recorded: int
    explications_already_imported: int


@dataclass(frozen=True)
class _Commit:
    sha: str
    author_date: datetime
    message: str


def _iter_commits(repo_root: Path) -> list[_Commit]:
    """
    Every real commit under `repo_root`, oldest first, as `git log`
    itself records it. Returns an empty list rather than raising when
    `git` is missing (`OSError`, the same convention
    `aistack.providers.host.provider.collect_temperatures` already
    uses) or `repo_root` is not a real git working tree (a non-zero
    exit) — "no history yet" is a real, representable state here, the
    same as every other importer's "nothing found" case.
    """

    try:
        result = subprocess.run(
            [
                "git",
                "log",
                "--reverse",
                f"--format=%H{_FIELD_SEP}%aI{_FIELD_SEP}%B{_RECORD_SEP}",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
    except OSError:
        return []

    if result.returncode != 0:
        return []

    commits: list[_Commit] = []
    for record in result.stdout.split(_RECORD_SEP):
        record = record.lstrip("\n")
        if not record.strip():
            continue

        sha, author_date_text, message = record.split(_FIELD_SEP, 2)
        commits.append(
            _Commit(
                sha=sha,
                author_date=datetime.fromisoformat(author_date_text),
                message=message.rstrip("\n"),
            )
        )

    return commits


def _scope(message: str) -> str | None:
    """
    A commit message's own conventional scope — the parenthesised
    token in its first line's `type(scope): ...` shape — or `None`
    when the first line does not have one. Never a guess at a subject
    from the rest of the message.
    """

    first_line = message.split("\n", 1)[0]
    match = _SCOPE_PATTERN.match(first_line)
    return match.group(1) if match else None


def import_commits(
    repo_root: Path = DEFAULT_REPO_ROOT,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> CommitsImportSummary:
    """
    Import every commit under `repo_root` whose message opens with a
    conventional `type(scope): message` first line as a `Proposed`
    `KnowledgeArtifact`, one Explication per commit, the scope as
    subject (`ADR-0011` § 7-8). A commit with no such scope is skipped
    and counted, never guessed at.
    """

    commits_seen = 0
    commits_skipped = 0
    explications_recorded = 0
    explications_already_imported = 0
    subjects_with_a_scoped_commit: set[str] = set()

    already_imported_by_subject: dict[str, set[str]] = {}

    for commit in _iter_commits(repo_root):
        commits_seen += 1
        subject = _scope(commit.message)

        if subject is None:
            commits_skipped += 1
            continue

        subjects_with_a_scoped_commit.add(subject)

        if subject not in already_imported_by_subject:
            already_imported_by_subject[subject] = {
                str(artifact.metadata["source_commit_sha"])
                for artifact in read_explication_history(subject, output_dir)
                if artifact.metadata.get("source_stream") == "commits"
                and "source_commit_sha" in artifact.metadata
            }

        if commit.sha in already_imported_by_subject[subject]:
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
            source=f"git:{commit.sha}",
            created_at=commit.author_date,
            updated_at=commit.author_date,
            confidence="Proposed",
            status=UNDECLARED,
            content=commit.message,
            metadata={
                "source_stream": "commits",
                "source_commit_sha": commit.sha,
                "explication_status": "Proposed",
            },
        )
        record_explication(artifact, output_dir=output_dir)
        already_imported_by_subject[subject].add(commit.sha)
        explications_recorded += 1

    return CommitsImportSummary(
        commits_seen=commits_seen,
        commits_skipped=commits_skipped,
        subjects_seen=len(subjects_with_a_scoped_commit),
        explications_recorded=explications_recorded,
        explications_already_imported=explications_already_imported,
    )
