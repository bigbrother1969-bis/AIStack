"""Log lines kept for the engine's explanation: relevant, cleaned, few, used and dropped (ADR-0032, O9)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from aistack.boot_checks.controls import Result
from aistack.boot_checks.excerpts import (
    LINE_LIMIT,
    MAX_CONTAINERS,
    MAX_LINES,
    Excerpt,
    basis,
    block,
    choose,
    clean_line,
    excerpts_for,
    read_container,
)
from aistack.boot_checks.explain import explain
from aistack.boot_checks.state import read_verdict, write_verdict
from tests.unit.boot_checks.test_explain import DB, FINE, NOW, _previous, answering

SINCE = datetime(2026, 11, 26, 6, 5, tzinfo=timezone.utc)
LOG = "\n".join(
    [
        "2026-11-26 06:09:31 LOG:  database system was not properly shut down; automatic recovery in progress",
        "2026-11-26 06:09:31 LOG:  connection received from 192.168.1.20",
        "2026-11-26 06:09:31 LOG:  redo is not required",
        "2026-11-26 06:09:31 LOG:  database system is ready to accept connections",
    ]
)


def test_secrets_addresses_and_opaque_strings_are_masked_and_the_line_is_cut() -> None:
    assert clean_line("login password=hunter2 ok") == "login password=*** ok"
    assert clean_line("connect postgres://app:s3cret@db:5432/x") == "connect postgres://***@db:5432/x"
    assert clean_line("from 10.0.0.7 by bob@example.org") == "from <ip> by <email>"
    assert clean_line("key " + "A" * 40) == "key <opaque>"
    assert clean_line("bad \x00\x07 bytes") == "bad bytes"
    assert len(clean_line("word " * 100)) == LINE_LIMIT


def test_only_the_relevant_lines_are_kept_the_last_few_without_repeats() -> None:
    noise = ["GET /health 200"] * 5
    repeated = ["ERROR: could not connect"] * 3
    many = [f"ERROR number {index}" for index in range(10)]

    assert choose(noise) == ()
    assert choose(repeated) == ("ERROR: could not connect",)
    assert choose(many) == tuple(f"ERROR number {index}" for index in range(10 - MAX_LINES, 10))


def test_a_container_log_is_read_since_the_start_and_cleaned() -> None:
    seen: list[list[str]] = []

    def run(command: list[str]) -> str | None:
        seen.append(command)

        return LOG

    item = read_container("immich_postgres", SINCE, run)

    assert seen == [["docker", "logs", "--tail", "400", "--since", SINCE.isoformat(), "immich_postgres"]]
    assert item is not None and item.read == 4 and item.lines[0].startswith("2026-11-26 06:09:31 LOG: database system was not properly")
    assert all("192.168" not in line for line in item.lines)


def test_a_name_that_is_not_a_container_name_is_never_given_to_docker() -> None:
    def run(command: list[str]) -> str | None:
        raise AssertionError("docker must not be called")

    for name in ("", "-v", "a b", "x;rm -rf /", "$(id)", "a" * 200):
        assert read_container(name, SINCE, run) is None


def test_a_log_that_cannot_be_read_adds_nothing() -> None:
    assert read_container("db", SINCE, lambda command: None) is None
    assert excerpts_for(DB, SINCE, lambda command: None) == ()


def test_only_the_controls_that_name_a_container_get_lines_and_not_too_many_containers() -> None:
    called: list[str] = []

    def run(command: list[str]) -> str | None:
        called.append(command[-1])

        return LOG

    assert excerpts_for(Result("mounts", "critical", "1 missing", ("/media/Data",)), SINCE, run) == ()
    many = Result("database_recovery", "warning", "6 database(s) recovered", tuple(f"db{index}" for index in range(6)))
    found = excerpts_for(many, SINCE, run)

    assert called == ["db0", "db1", "db2"] and len(found) == MAX_CONTAINERS


def test_the_engine_gets_the_lines_and_the_explanation_keeps_only_how_many() -> None:
    ask, calls = answering("Les bases ont redémarré après un arrêt brutal.")
    found = (Excerpt("immich_postgres", ("redo is not required", "ready to accept connections"), 40),)

    said = explain((DB,), (), [DB, FINE], ask, NOW, 5.0, excerpts=lambda result: found)

    assert "log lines of immich_postgres (cleaned, 2 of 40 read)" in calls[0][3] and "- redo is not required" in calls[0][3]
    assert said[0].basis == ("2 log line(s) of immich_postgres kept (40 read)",)
    assert "redo is not required" not in repr(said)


def test_without_lines_or_with_a_failing_reader_the_anomaly_is_explained_as_before() -> None:
    ask, calls = answering("dit")

    def boom(result: Result) -> tuple[Excerpt, ...]:
        raise OSError("no docker")

    assert explain((DB,), (), [DB], ask, NOW, 5.0)[0].basis == ()
    assert explain((DB,), (), [DB], ask, NOW, 5.0, excerpts=boom)[0].text == "dit"
    assert "log lines" not in calls[0][3] and "log lines" not in calls[1][3]


def test_a_silent_engine_keeps_no_basis_and_the_verdict_never_stores_a_line(tmp_path: Path) -> None:
    ask, _ = answering("", reachable=False)
    found = (Excerpt("db", ("secret-looking line",), 3),)

    assert explain((DB,), (), [DB], ask, NOW, 5.0, excerpts=lambda result: found)[0].basis == ()

    ask, _ = answering("dit")
    said = explain((DB,), (), [DB], ask, NOW, 5.0, excerpts=lambda result: found)
    write_verdict(tmp_path, _previous(*said))
    stored = read_verdict(tmp_path)

    assert stored is not None and stored.explanations[0].basis == ("1 log line(s) of db kept (3 read)",)
    assert "secret-looking line" not in (tmp_path / "boot-check.json").read_text(encoding="utf-8")


def test_block_and_basis_say_each_container() -> None:
    two = (Excerpt("a", ("x",), 1), Excerpt("b", ("y", "z"), 9))

    assert block(two).count("log lines of") == 2 and basis(two)[1] == "2 log line(s) of b kept (9 read)"
    assert block(()) == "" and basis(()) == ()
