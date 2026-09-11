"""
`aistack.cli.console_render` — `PLAN-J11`'s console
(`claude/PLAN-J11-CONSOLE-2026-09-11.md` § 2/§ 4).

Mirrors `test_health_render.py`'s own end-to-end style for the "does
`main()` write the artifact" test — the same GOV-0002/OS-044
discipline: a command is only proven wired by actually calling it.
This module additionally exercises the one piece no other `cli/*`
command has: `PUBLIC_DIR`'s relative symlinks, the fix for the gap
`PLAN-J11` § 4 found — nothing before this command ever served
`reports/generated/` over HTTP at all.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.cli import console_render as cli


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------------------
# main() — end to end
# --------------------------------------------------------------------


def test_main_writes_the_console_html_artifact(workspace):
    cli.main()

    path = workspace / "reports" / "generated" / "console.html"
    assert path.exists()

    document = path.read_text(encoding="utf-8")
    assert document.startswith("<!doctype html>")
    assert "Selection UI" in document
    assert "Cockpit Santé" in document


def test_main_prints_a_confirmation_line(workspace, capsys):
    cli.main()

    captured = capsys.readouterr()
    assert "Console written to" in captured.out
    assert "4 link(s)" in captured.out
    assert "served from" in captured.out


def test_main_creates_the_public_directory_with_an_index(workspace):
    cli.main()

    index = workspace / "reports" / "generated" / "public" / "index.html"
    assert index.exists()
    assert "console.html" in index.read_text(encoding="utf-8")


def test_main_symlinks_the_three_served_artifacts_into_public(workspace):
    cli.main()

    public_dir = workspace / "reports" / "generated" / "public"

    for name, target in (
        ("console.html", "../console.html"),
        ("architecture.html", "../architecture.html"),
        ("health.html", "../health.html"),
    ):
        link = public_dir / name
        assert link.is_symlink()
        assert str(link.readlink()) == target


def test_the_console_html_is_reachable_through_its_own_symlink(workspace):
    cli.main()

    public_dir = workspace / "reports" / "generated" / "public"

    assert (public_dir / "console.html").read_text(encoding="utf-8") == (
        workspace / "reports" / "generated" / "console.html"
    ).read_text(encoding="utf-8")


def test_running_main_twice_is_idempotent(workspace):
    cli.main()
    cli.main()

    public_dir = workspace / "reports" / "generated" / "public"
    assert (public_dir / "console.html").is_symlink()


def test_history_lives_beside_the_generated_file_not_inside_public(workspace):
    """
    `PLAN-J11` § 4: `PUBLIC_DIR` exposes exactly three pages, never
    `write_artifact_with_history`'s own `history/` subdirectory — that
    subdirectory is created beside `console.html`
    (`reports/generated/history/console/`), never inside
    `reports/generated/public/`, so a server rooted at `PUBLIC_DIR`
    never reaches it.
    """

    cli.main()

    generated_dir = workspace / "reports" / "generated"
    public_dir = generated_dir / "public"

    assert (generated_dir / "history" / "console").is_dir()
    assert not (public_dir / "history").exists()


# --------------------------------------------------------------------
# _ensure_public_symlink — the one piece of plumbing this command
# owns outright
# --------------------------------------------------------------------


def test_ensure_public_symlink_creates_a_new_link(tmp_path: Path):
    link_path = tmp_path / "architecture.html"

    cli._ensure_public_symlink(link_path, Path("../architecture.html"))

    assert link_path.is_symlink()
    assert str(link_path.readlink()) == "../architecture.html"


def test_ensure_public_symlink_leaves_a_matching_link_alone(tmp_path: Path):
    link_path = tmp_path / "architecture.html"
    link_path.symlink_to(Path("../architecture.html"))
    inode_before = link_path.lstat().st_ino

    cli._ensure_public_symlink(link_path, Path("../architecture.html"))

    assert link_path.lstat().st_ino == inode_before


def test_ensure_public_symlink_repairs_a_link_pointing_elsewhere(tmp_path: Path):
    link_path = tmp_path / "architecture.html"
    link_path.symlink_to(Path("../somewhere-else.html"))

    cli._ensure_public_symlink(link_path, Path("../architecture.html"))

    assert str(link_path.readlink()) == "../architecture.html"


def test_ensure_public_symlink_refuses_to_clobber_a_real_file(tmp_path: Path):
    link_path = tmp_path / "architecture.html"
    link_path.write_text("not managed by this command", encoding="utf-8")

    with pytest.raises(ValueError, match="not a symlink this command manages"):
        cli._ensure_public_symlink(link_path, Path("../architecture.html"))

    assert link_path.read_text(encoding="utf-8") == "not managed by this command"


# --------------------------------------------------------------------
# DEFAULT_CONSOLE_LINKS — the real, governed file
# --------------------------------------------------------------------


def test_the_default_console_links_definition_exists():
    assert cli.DEFAULT_CONSOLE_LINKS.exists()
