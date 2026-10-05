"""
`aistack.explications.from_commits` — against a real, throwaway git
repository this module's own fixtures build and commit into, not a
fabricated `git log` transcript: the parser reads real `git log`
output, so it is tested against real `git log` output.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from aistack.explications import read_explication_history
from aistack.explications.from_commits import import_commits


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "commit.gpgsign=false", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _make_repo(tmp_path: Path, commits: list[tuple[str, str]]) -> Path:
    """
    A throwaway git repository under `tmp_path`, with one empty commit
    per `(message, author_date_iso)` pair, oldest first — exactly the
    shape `import_commits` reads via `git log --reverse`.
    """

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch=main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")

    for message, author_date in commits:
        env = dict(os.environ)
        env.update(
            {
                "GIT_AUTHOR_NAME": "Test",
                "GIT_AUTHOR_EMAIL": "test@example.com",
                "GIT_AUTHOR_DATE": author_date,
                "GIT_COMMITTER_NAME": "Test",
                "GIT_COMMITTER_EMAIL": "test@example.com",
                "GIT_COMMITTER_DATE": author_date,
            }
        )
        subprocess.run(
            [
                "git",
                "-c",
                "commit.gpgsign=false",
                "commit",
                "--allow-empty",
                "-m",
                message,
            ],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

    return repo


def test_a_commit_with_a_conventional_scope_is_imported_as_an_explication(
    tmp_path: Path,
):
    repo = _make_repo(
        tmp_path,
        [("feat(kernel): add the ticking heartbeat", "2026-09-20T10:00:00+00:00")],
    )
    output_dir = tmp_path / "explications"

    summary = import_commits(repo, output_dir)

    assert summary.commits_seen == 1
    assert summary.commits_skipped == 0
    assert summary.subjects_seen == 1
    assert summary.explications_recorded == 1

    history = read_explication_history("kernel", output_dir)
    assert len(history) == 1
    artifact = history[0]
    assert artifact.source.startswith("git:")
    assert artifact.confidence == "Proposed"
    assert artifact.created_at == datetime(2026, 9, 20, 10, 0, 0, tzinfo=UTC)
    assert "feat(kernel): add the ticking heartbeat" in artifact.content
    assert artifact.metadata["source_stream"] == "commits"


def test_a_commit_with_no_conventional_scope_is_skipped(tmp_path: Path):
    repo = _make_repo(
        tmp_path,
        [("docs: record the 1.2.1 image publication", "2026-09-20T10:00:00+00:00")],
    )
    output_dir = tmp_path / "explications"

    summary = import_commits(repo, output_dir)

    assert summary.commits_seen == 1
    assert summary.commits_skipped == 1
    assert summary.explications_recorded == 0
    assert summary.subjects_seen == 0


def test_import_is_idempotent_by_commit_sha(tmp_path: Path):
    repo = _make_repo(
        tmp_path,
        [("feat(kernel): add the ticking heartbeat", "2026-09-20T10:00:00+00:00")],
    )
    output_dir = tmp_path / "explications"

    import_commits(repo, output_dir)
    second = import_commits(repo, output_dir)

    assert second.explications_recorded == 0
    assert second.explications_already_imported == 1
    assert len(read_explication_history("kernel", output_dir)) == 1


def test_a_non_git_directory_yields_no_commits(tmp_path: Path):
    not_a_repo = tmp_path / "plain"
    not_a_repo.mkdir()
    output_dir = tmp_path / "explications"

    summary = import_commits(not_a_repo, output_dir)

    assert summary.commits_seen == 0
    assert summary.explications_recorded == 0


def test_two_commits_sharing_a_scope_in_one_run_both_survive(
    tmp_path: Path, monkeypatch
):
    """
    Two writes to the same subject in the same wall-clock second — the
    clock is frozen, nothing waits — both read back (1.9: Explications
    are read version by version, `aistack.history.every_version`).
    """

    import aistack.generators.history as history_module

    monkeypatch.setattr(
        history_module, "wall_clock", lambda: datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)
    )

    repo = _make_repo(
        tmp_path,
        [
            ("feat(kernel): first change", "2026-09-20T10:00:00+00:00"),
            ("fix(kernel): second change", "2026-09-20T10:05:00+00:00"),
        ],
    )
    output_dir = tmp_path / "explications"

    summary = import_commits(repo, output_dir)

    assert summary.explications_recorded == 2
    history = read_explication_history("kernel", output_dir)
    assert len(history) == 2
    assert "first change" in history[0].content
    assert "second change" in history[1].content


def test_import_on_an_empty_repository_does_nothing(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "--quiet", "--initial-branch=main")
    output_dir = tmp_path / "explications"

    summary = import_commits(repo, output_dir)

    assert summary.commits_seen == 0
    assert summary.explications_recorded == 0
