"""
`aistack.explications.from_pra_tests` — against a real-shaped
`pra_tests.yml` fixture (the same bold-lede comment convention the
real file already uses), not a synthetic JSON stand-in. Fixtures below
mirror the real file's own header and dated-block structure measured
directly from `src/aistack/pra/definitions/pra_tests.yml` on
2026-09-27.
"""

from __future__ import annotations

from pathlib import Path

from aistack.explications import read_explication_history
from aistack.explications.from_pra_tests import import_pra_tests_comments

_HEADER = """\
# PRA (restore) test records — OPS-0009's own declared values.
#
# Declared 2026-09-23 by the owner, the same honest header the real
# file carries before any dated block begins.
#
"""


def _write(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "pra_tests.yml"
    path.write_text(_HEADER + body + "\nmax_age_days: 90\n\nservices: []\n", encoding="utf-8")
    return path


def test_import_records_one_explication_per_subject_date_block(tmp_path: Path):
    body = (
        "# **`arrstack` recorded as `failed`, 2026-09-26.** The owner ran a\n"
        "# real restore attempt and found nothing under arrstack in the\n"
        "# archive at all.\n"
    )
    pra_tests_path = _write(tmp_path, body)
    output_dir = tmp_path / "explications"

    summary = import_pra_tests_comments(pra_tests_path, output_dir)

    assert summary.blocks_seen == 1
    assert summary.blocks_skipped == 0
    assert summary.subjects_seen == 1
    assert summary.explications_recorded == 1
    assert summary.explications_already_imported == 0

    history = read_explication_history("arrstack", output_dir)
    assert len(history) == 1
    artifact = history[0]
    assert artifact.id == "arrstack"
    assert artifact.confidence == "Proposed"
    assert artifact.source == "file:pra_tests.yml"
    assert "recorded as `failed`" in artifact.content
    assert artifact.metadata["source_stream"] == "pra-tests"
    assert artifact.metadata["source_instant"] == "2026-09-26"


def test_two_same_day_blocks_for_the_same_subject_are_merged_into_one_explication(
    tmp_path: Path,
):
    """
    `arrstack`'s own real blocks: recorded as failed, then corrected to
    success the same day. Day-granularity dates give no way to order
    two same-day writes as distinct historical instants without
    tripping `available_instants`'s own same-second collision
    collapse — so this is one merged Explication, not two, with the
    narrative order preserved.
    """

    body = (
        "# **`arrstack` recorded as `failed`, 2026-09-26.** A real restore\n"
        "# attempt found nothing under arrstack in the archive.\n"
        "#\n"
        "# **`arrstack` corrected to `success`, same day (2026-09-26).** A\n"
        "# dedicated backup script was written and a real restore test\n"
        "# followed, completing cleanly.\n"
    )
    pra_tests_path = _write(tmp_path, body)
    output_dir = tmp_path / "explications"

    summary = import_pra_tests_comments(pra_tests_path, output_dir)

    assert summary.blocks_seen == 2
    assert summary.subjects_seen == 1
    assert summary.explications_recorded == 1

    history = read_explication_history("arrstack", output_dir)
    assert len(history) == 1
    content = history[0].content
    assert content.index("recorded as `failed`") < content.index("corrected to `success`")


def test_import_is_idempotent_against_unchanged_pra_tests_yml(tmp_path: Path):
    body = (
        "# **`raspberry` corrected to `success`, same day (2026-09-26).** A\n"
        "# real restic restore completed cleanly.\n"
    )
    pra_tests_path = _write(tmp_path, body)
    output_dir = tmp_path / "explications"

    import_pra_tests_comments(pra_tests_path, output_dir)
    second = import_pra_tests_comments(pra_tests_path, output_dir)

    assert second.explications_recorded == 0
    assert second.explications_already_imported == 1
    assert len(read_explication_history("raspberry", output_dir)) == 1


def test_a_block_with_no_backtick_subject_is_skipped(tmp_path: Path):
    body = "# **Vikunja gap closed, same day (2026-09-26).** A dedicated dump\n# now covers its database too.\n"
    pra_tests_path = _write(tmp_path, body)
    output_dir = tmp_path / "explications"

    summary = import_pra_tests_comments(pra_tests_path, output_dir)

    assert summary.blocks_seen == 1
    assert summary.blocks_skipped == 1
    assert summary.explications_recorded == 0
    assert read_explication_history("vikunja", output_dir) == []


def test_a_block_with_no_date_is_skipped(tmp_path: Path):
    body = "# **`arrstack` has a real backup now.** No date is stated here.\n"
    pra_tests_path = _write(tmp_path, body)
    output_dir = tmp_path / "explications"

    summary = import_pra_tests_comments(pra_tests_path, output_dir)

    assert summary.blocks_skipped == 1
    assert summary.explications_recorded == 0


def test_text_before_the_first_dated_block_is_not_imported(tmp_path: Path):
    """
    The file's own provenance header (declared 2026-09-23, no bold
    lede) names no subject and states no per-block fact — it is not a
    dated block and must not be treated as one.
    """

    pra_tests_path = _write(tmp_path, "")
    output_dir = tmp_path / "explications"

    summary = import_pra_tests_comments(pra_tests_path, output_dir)

    assert summary.blocks_seen == 0
    assert summary.explications_recorded == 0


def test_import_on_a_file_with_no_dated_blocks_does_nothing(tmp_path: Path):
    pra_tests_path = tmp_path / "pra_tests.yml"
    pra_tests_path.write_text("max_age_days: 90\n\nservices: []\n", encoding="utf-8")
    output_dir = tmp_path / "explications"

    summary = import_pra_tests_comments(pra_tests_path, output_dir)

    assert summary.blocks_seen == 0
    assert summary.explications_recorded == 0
