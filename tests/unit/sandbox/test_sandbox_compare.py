from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from aistack.sandbox.compare import (
    MARIADB,
    POSTGRES,
    compare,
    compare_files,
    compare_tables,
    live_mount_source,
    summary_lines,
)
from aistack.sandbox.run import CommandResult, SandboxRun

ROWS = {
    "sandbox-db": {"wp_posts": 100, "wp_options": 50, "wp_only_backup": 1},
    "wordpress_db": {"wp_posts": 103, "wp_options": 50, "wp_new": 2},
}


class FakeDocker:
    def __init__(self, separator: str = "\t") -> None:
        self.calls: list[list[str]] = []
        self.separator = separator

    def __call__(self, args: Sequence[str], timeout: float) -> CommandResult:
        args = list(args)
        self.calls.append(args)
        if args[0] == "inspect":
            return CommandResult(0, "/var/www/html|/srv/wordpress/html\n/var/www/html/wp-content|/srv/wordpress/wp-content\n")
        container = next(a for a in args[1:] if not a.startswith("-") and not a.startswith("DB="))
        tables = ROWS[container]
        query = args[-1]
        if "COUNT(*)" not in query:
            return CommandResult(0, "\n".join(tables) + "\n")
        lines = [
            f"{name}{self.separator}{count}" for name, count in tables.items() if f"'{name}'" in query
        ]
        return CommandResult(0, "\n".join(lines) + "\n")


def _run(tmp_path: Path, docker: FakeDocker) -> SandboxRun:
    return SandboxRun("wordpress", tmp_path, docker)


def test_rows_are_compared_table_by_table_biggest_gap_first(tmp_path: Path):
    docker = FakeDocker()
    result = compare_tables(
        _run(tmp_path, docker), engine=MARIADB, sandbox_container="sandbox-db", sandbox_database="wordpress",
        live_container="wordpress_db",
    )

    assert result["tables_compared"] == 2
    assert (result["rows_backup"], result["rows_live"]) == (150, 153)
    assert result["tables"][0] == {"table": "wp_posts", "backup": 100, "live": 103, "gap": 3}
    assert result["only_in_backup"] == ["wp_only_backup"]
    assert result["only_live"] == ["wp_new"]


def test_the_live_database_is_only_counted_with_its_own_environment(tmp_path: Path):
    docker = FakeDocker()
    compare_tables(
        _run(tmp_path, docker), engine=MARIADB, sandbox_container="sandbox-db", sandbox_database="wordpress",
        live_container="wordpress_db",
    )

    live = [call for call in docker.calls if "wordpress_db" in call]
    assert live
    for call in live:
        assert call[0] == "exec"
        assert not any(arg.startswith("DB=") for arg in call)
        query = call[-1].upper()
        assert query.startswith("SELECT")
        assert not any(word in query for word in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER"))
        assert "PASSWORD=" not in " ".join(call[:-3])


def test_postgres_counts_are_read_with_its_separator(tmp_path: Path):
    result = compare_tables(
        _run(tmp_path, FakeDocker(separator="|")), engine=POSTGRES, sandbox_container="sandbox-db",
        sandbox_database="immich", live_container="wordpress_db",
    )

    assert result["rows_live"] == 153


def test_files_are_compared_folder_by_folder(tmp_path: Path):
    backup, live = tmp_path / "backup", tmp_path / "live"
    for root, count in ((backup, 2), (live, 3)):
        (root / "uploads").mkdir(parents=True)
        for index in range(count):
            (root / "uploads" / f"{index}.jpg").write_bytes(b"x" * 10)
        (root / "index.php").write_text("<?php")

    result = compare_files(backup, live)

    assert (result["files_backup"], result["files_live"]) == (3, 4)
    assert result["folders"][0]["folder"] == "uploads" and result["folders"][0]["files_gap"] == 1


def test_where_the_live_service_keeps_its_files_is_read_from_its_mounts(tmp_path: Path):
    assert live_mount_source(_run(tmp_path, FakeDocker()), "wp_app", "/var/www/html/wp-content") == Path(
        "/srv/wordpress/wp-content"
    )


def test_a_part_that_cannot_be_compared_is_said_and_the_others_still_are(tmp_path: Path):
    run = _run(tmp_path, FakeDocker())
    run.compare = True

    compare(run, [
        ("wp-content", lambda: compare_files(tmp_path, tmp_path / "missing")),
        ("base", lambda: compare_tables(
            run, engine=MARIADB, sandbox_container="sandbox-db", sandbox_database="wordpress",
            live_container="wordpress_db",
        )),
    ])

    comparison = run.facts["comparison"]
    assert "cannot be read" in comparison["wp-content"]["not_compared"]
    assert comparison["base"]["tables_compared"] == 2
    text = "\n".join(summary_lines(comparison))
    assert "wp_posts : 100 → 103 (+3)" in text
    assert "non comparé" in text
    assert run.succeeded is False  # a comparison never makes a check


def test_no_comparison_unless_asked(tmp_path: Path):
    run = _run(tmp_path, FakeDocker())

    compare(run, [("base", lambda: {"x": 1})])

    assert "comparison" not in run.facts and not run.steps
