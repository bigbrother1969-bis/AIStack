from __future__ import annotations

from pathlib import Path

import pytest

from aistack.restart_watch import guard, journal
from aistack.restart_watch.load import load_restart_watch_yaml

SHIPPED = Path(__file__).resolve().parents[3] / "src/aistack/restart_watch/definitions/restart_watch.yml"


def test_two_attempts_an_hour_then_the_container_waits():
    attempts: guard.Attempts = {}

    assert guard.allowed(attempts, "firefly", 1000.0, 2)
    guard.record(attempts, "firefly", 1000.0)
    guard.record(attempts, "firefly", 1100.0)

    assert not guard.allowed(attempts, "firefly", 1200.0, 2)
    assert guard.allowed(attempts, "firefly", 1000.0 + 3600, 2)
    assert guard.allowed(attempts, "other", 1200.0, 2)


def test_attempts_survive_a_restart_of_the_watch(tmp_path: Path):
    guard.write_attempts(tmp_path, {"a": [1.0, 2.0]})

    assert guard.read_attempts(tmp_path) == {"a": [1.0, 2.0]}
    assert guard.read_attempts(tmp_path / "nowhere") == {}


def test_the_journal_keeps_the_newest_first_and_trims(tmp_path: Path):
    for number in range(journal.TRIM_AT + 5):
        journal.append(tmp_path, journal.Entry(f"t{number}", journal.RESTARTED, "c", ("unhealthy",), "ok"))

    lines = (tmp_path / journal.JOURNAL_FILE).read_text(encoding="utf-8").splitlines()
    newest = journal.read(tmp_path, limit=3)

    assert len(lines) <= journal.KEPT + 5
    assert [e.at for e in newest] == [f"t{journal.TRIM_AT + 4}", f"t{journal.TRIM_AT + 3}", f"t{journal.TRIM_AT + 2}"]


def test_a_damaged_journal_line_is_skipped(tmp_path: Path):
    (tmp_path / journal.JOURNAL_FILE).write_text('not json\n{"at":"t","event":"restarted","container":"c"}\n', encoding="utf-8")

    assert [e.container for e in journal.read(tmp_path)] == ["c"]


def test_the_shipped_declaration_loads_with_the_decided_defaults():
    definition = load_restart_watch_yaml(SHIPPED)

    assert (definition.window_minutes, definition.max_attempts_per_hour, definition.confirm_cycles) == (30, 2, 2)
    assert definition.after == {} and definition.never == () and definition.probes == {}


def test_the_owner_s_declaration_is_read(tmp_path: Path):
    path = tmp_path / "w.yml"
    path.write_text(
        "never: [frigate]\nafter:\n  firefly: [firefly_db]\nprobes:\n  scrutiny:\n    url: http://127.0.0.1:8080/api/health\n    timeout_seconds: 3\n",
        encoding="utf-8",
    )

    definition = load_restart_watch_yaml(path)

    assert definition.never == ("frigate",)
    assert definition.after == {"firefly": ("firefly_db",)}
    assert definition.probes["scrutiny"].timeout_seconds == 3.0


@pytest.mark.parametrize(
    "text",
    ["window_minutes: 0\n", "never: frigate\n", "probes:\n  x: {}\n", "- a\n", "after: [a]\n"],
)
def test_a_wrong_declaration_says_so(tmp_path: Path, text: str):
    path = tmp_path / "w.yml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError):
        load_restart_watch_yaml(path)
