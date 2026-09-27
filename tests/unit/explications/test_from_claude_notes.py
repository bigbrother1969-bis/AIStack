"""
`aistack.explications.from_claude_notes` — against fixtures shaped
exactly like the real `claude/*.md` corpus measured 2026-09-27: 4 of 5
real files declare `artifact.id`/`artifact.updated` frontmatter, one
(`PLAN-VS2-2.4-PROTOCOL-2026-09-25.md`) declares none at all.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from aistack.explications import read_explication_history
from aistack.explications.from_claude_notes import import_claude_notes

_WITH_FRONTMATTER = """\
---
artifact:
  id: SESSION-2026-09-25-VS2-2.4-RERUN
  title: Session — deuxieme execution
  type: Session Note
  status: Execute.
  created: 2026-09-25
  updated: 2026-09-25
---

# Body

Some real session note content.
"""

_WITHOUT_FRONTMATTER = """\
# VS-2.4 — Protocol for a Cross-Model Run

**Status: project working note, not governed heritage.** No frontmatter here.
"""


def _write(tmp_path: Path, name: str, content: str) -> Path:
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    path = claude_dir / name
    path.write_text(content, encoding="utf-8")
    return claude_dir


def test_import_records_one_explication_using_frontmatter_id_and_date(tmp_path: Path):
    claude_dir = _write(
        tmp_path, "SESSION-2026-09-25-vs2-2.4-rerun.md", _WITH_FRONTMATTER
    )
    output_dir = tmp_path / "explications"

    summary = import_claude_notes(claude_dir, output_dir)

    assert summary.notes_seen == 1
    assert summary.notes_skipped == 0
    assert summary.explications_recorded == 1

    history = read_explication_history("SESSION-2026-09-25-VS2-2.4-RERUN", output_dir)
    assert len(history) == 1
    artifact = history[0]
    assert artifact.source == "file:claude/SESSION-2026-09-25-vs2-2.4-rerun.md"
    assert artifact.created_at == datetime(2026, 9, 25, tzinfo=UTC)
    assert artifact.confidence == "Proposed"
    assert artifact.content == _WITH_FRONTMATTER
    assert artifact.metadata["source_stream"] == "claude-notes"


def test_a_note_with_no_frontmatter_falls_back_to_filename_stem_and_embedded_date(
    tmp_path: Path,
):
    claude_dir = _write(
        tmp_path, "PLAN-VS2-2.4-PROTOCOL-2026-09-25.md", _WITHOUT_FRONTMATTER
    )
    output_dir = tmp_path / "explications"

    summary = import_claude_notes(claude_dir, output_dir)

    assert summary.notes_skipped == 0
    assert summary.explications_recorded == 1

    history = read_explication_history(
        "PLAN-VS2-2.4-PROTOCOL-2026-09-25", output_dir
    )
    assert len(history) == 1
    assert history[0].created_at == datetime(2026, 9, 25, tzinfo=UTC)


def test_import_is_idempotent_against_unchanged_note_content(tmp_path: Path):
    claude_dir = _write(
        tmp_path, "SESSION-2026-09-25-vs2-2.4-rerun.md", _WITH_FRONTMATTER
    )
    output_dir = tmp_path / "explications"

    import_claude_notes(claude_dir, output_dir)
    second = import_claude_notes(claude_dir, output_dir)

    assert second.explications_recorded == 0
    assert second.explications_already_imported == 1
    assert (
        len(read_explication_history("SESSION-2026-09-25-VS2-2.4-RERUN", output_dir))
        == 1
    )


def test_editing_a_notes_content_records_a_new_explication_version(
    tmp_path: Path, monkeypatch
):
    """
    A `claude/` note carries no separate "this changed" marker of its
    own — the file's own text changing is the only real signal. Two
    real writes a second apart, not two in the same process tick —
    `available_instants` collapses same-second writes to one
    historical moment, so the clock is controlled here the same way
    `tests/unit/generators/test_history.py
    ::test_two_writes_in_the_same_second_both_survive` controls it.
    """

    import aistack.generators.history as history_module

    class FrozenDatetime(history_module.datetime):
        _instant = datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)

        @classmethod
        def now(cls, tz=None):
            return cls._instant

    monkeypatch.setattr(history_module, "datetime", FrozenDatetime)

    claude_dir = _write(
        tmp_path, "SESSION-2026-09-25-vs2-2.4-rerun.md", _WITH_FRONTMATTER
    )
    output_dir = tmp_path / "explications"

    FrozenDatetime._instant = datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)
    import_claude_notes(claude_dir, output_dir)

    edited = _WITH_FRONTMATTER.replace("Some real session note content.", "Edited.")
    (claude_dir / "SESSION-2026-09-25-vs2-2.4-rerun.md").write_text(
        edited, encoding="utf-8"
    )

    FrozenDatetime._instant = datetime(2026, 9, 27, 12, 0, 1, tzinfo=UTC)
    summary = import_claude_notes(claude_dir, output_dir)

    assert summary.explications_recorded == 1
    history = read_explication_history("SESSION-2026-09-25-VS2-2.4-RERUN", output_dir)
    assert len(history) == 2
    assert history[-1].content == edited


def test_a_note_with_no_frontmatter_and_no_date_in_filename_is_skipped(
    tmp_path: Path,
):
    claude_dir = _write(tmp_path, "UNDATED-NOTE.md", _WITHOUT_FRONTMATTER)
    output_dir = tmp_path / "explications"

    summary = import_claude_notes(claude_dir, output_dir)

    assert summary.notes_seen == 1
    assert summary.notes_skipped == 1
    assert summary.explications_recorded == 0


def test_import_on_an_empty_directory_does_nothing(tmp_path: Path):
    claude_dir = tmp_path / "claude"
    claude_dir.mkdir()
    output_dir = tmp_path / "explications"

    summary = import_claude_notes(claude_dir, output_dir)

    assert summary.notes_seen == 0
    assert summary.explications_recorded == 0
