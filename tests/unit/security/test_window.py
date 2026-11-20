"""The maintenance window of the owner's own work (ADR-0028 T4a)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack.cli import security_window
from aistack.security import window

NOW = datetime(2026, 11, 20, 12, 0, tzinfo=timezone.utc)


def test_durations() -> None:
    assert window.parse_duration("2h") == timedelta(hours=2)
    assert window.parse_duration("90m") == timedelta(minutes=90)
    assert window.parse_duration("1,5") == timedelta(minutes=90)

    for bad in ("", "soon", "-1h", "2 days"):
        with pytest.raises(ValueError):
            window.parse_duration(bad)


def test_a_window_is_open_then_ends_by_itself(tmp_path: Path) -> None:
    opened = window.open_window(tmp_path, NOW, timedelta(hours=2), 4)

    assert window.current(tmp_path, NOW + timedelta(hours=1)) == opened
    assert window.current(tmp_path, NOW + timedelta(hours=2)) is None
    assert window.close_if_expired(tmp_path, NOW + timedelta(hours=1)) is None
    assert window.close_if_expired(tmp_path, NOW + timedelta(hours=3)) == opened
    assert window.read(tmp_path) is None
    assert window.close_if_expired(tmp_path, NOW + timedelta(hours=4)) is None


def test_a_window_is_bounded_by_the_declared_maximum(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at most 4 h"):
        window.open_window(tmp_path, NOW, timedelta(hours=5), 4)

    with pytest.raises(ValueError):
        window.open_window(tmp_path, NOW, timedelta(0), 4)

    assert window.read(tmp_path) is None


def test_ending_by_hand(tmp_path: Path) -> None:
    assert window.end(tmp_path, NOW) is False
    window.open_window(tmp_path, NOW, timedelta(hours=1), 4)

    assert window.end(tmp_path, NOW + timedelta(minutes=10)) is True
    assert window.current(tmp_path, NOW + timedelta(minutes=11)) is None


def test_every_opening_and_ending_is_journalled(tmp_path: Path) -> None:
    window.open_window(tmp_path, NOW, timedelta(hours=1), 4)
    window.end(tmp_path, NOW + timedelta(minutes=5))
    window.open_window(tmp_path, NOW + timedelta(hours=2), timedelta(hours=1), 4)
    window.close_if_expired(tmp_path, NOW + timedelta(hours=4))

    events = [json.loads(line)["event"] for line in (tmp_path / window.JOURNAL).read_text(encoding="utf-8").splitlines()]
    assert events == ["opened", "ended", "opened", "expired"]


def test_an_unreadable_state_is_no_window(tmp_path: Path) -> None:
    (tmp_path / window.STATE).write_text("{not json", encoding="utf-8")
    assert window.current(tmp_path, NOW) is None
    assert window.close_if_expired(tmp_path, NOW) is None


def test_the_command_goes_through_the_runtime(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    now = datetime.now(timezone.utc)

    assert security_window.main(["--show", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "No window is open.\n"

    assert security_window.main(["--for", "2h", str(tmp_path)]) == 0
    said = capsys.readouterr().out
    assert said.startswith("A maintenance window is open until ")
    assert "(119 min left)" in said or "(120 min left)" in said
    assert window.current(tmp_path, now) is not None

    assert security_window.main(["--for", "9h", str(tmp_path)]) == 2
    assert "Not opened: a window lasts at most 4 h" in capsys.readouterr().out

    assert security_window.main(["--for", "soon", str(tmp_path)]) == 2
    assert "not a duration" in capsys.readouterr().out

    assert security_window.main(["--show", str(tmp_path)]) == 0
    assert "open until" in capsys.readouterr().out

    assert security_window.main(["--end", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "The window is closed.\n"
    assert security_window.main(["--end", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "No window is open.\n"
    assert window.current(tmp_path, now) is None


def test_the_task_is_registered_and_traced(tmp_path: Path) -> None:
    security_window.main(["--for", "1h", str(tmp_path)])

    trace = json.loads((tmp_path / "execution-trace.json").read_text(encoding="utf-8"))
    assert "security.window" in json.dumps(trace)
