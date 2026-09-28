from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from aistack.cli.docker_events_monitor import (
    USAGE,
    load_checkpoint,
    log_cycle,
    parse,
    run_cycle,
    save_checkpoint,
)

ONE_EVENT_LINE = (
    json.dumps(
        {
            "Type": "container",
            "Action": "start",
            "Actor": {"ID": "abc123", "Attributes": {"name": "some-container"}},
            "time": 1790000000,
        }
    )
    + "\n"
)


def _docker_events(stdout: str = "", returncode: int = 0):
    return patch(
        "subprocess.run",
        return_value=subprocess.CompletedProcess(
            args=[], returncode=returncode, stdout=stdout, stderr=""
        ),
    )


def test_parse_defaults():
    output_path, checkpoint_path, once, dry_run = parse([])

    assert output_path.name == "docker-events.json"
    assert checkpoint_path.name == "checkpoint.json"
    assert once is False
    assert dry_run is False


def test_parse_accepts_output_and_checkpoint_overrides():
    output_path, checkpoint_path, _, _ = parse(
        ["--output", "/tmp/out.json", "--checkpoint", "/tmp/cp.json"]
    )

    assert output_path == Path("/tmp/out.json")
    assert checkpoint_path == Path("/tmp/cp.json")


def test_parse_accepts_once_and_dry_run_together():
    _, _, once, dry_run = parse(["--once", "--dry-run"])

    assert once is True
    assert dry_run is True


def test_parse_prints_usage_and_exits_on_help():
    with pytest.raises(SystemExit) as excinfo:
        parse(["--help"])

    assert excinfo.value.code == 0


def test_parse_rejects_an_unknown_argument():
    with pytest.raises(SystemExit) as excinfo:
        parse(["--nonsense"])

    assert excinfo.value.code == 2


def test_usage_names_every_flag_parse_accepts():
    for flag in ("--output", "--checkpoint", "--once", "--dry-run"):
        assert flag in USAGE


def test_load_checkpoint_is_none_when_the_file_does_not_exist(tmp_path: Path):
    assert load_checkpoint(tmp_path / "missing.json") is None


def test_load_checkpoint_is_none_on_corrupted_content(tmp_path: Path):
    checkpoint_path = tmp_path / "checkpoint.json"
    checkpoint_path.write_text("not json", encoding="utf-8")

    assert load_checkpoint(checkpoint_path) is None


def test_save_and_load_checkpoint_round_trips(tmp_path: Path):
    checkpoint_path = tmp_path / "checkpoint.json"

    save_checkpoint(checkpoint_path, "2026-09-28T10:00:10+00:00")

    assert load_checkpoint(checkpoint_path) == "2026-09-28T10:00:10+00:00"


def test_log_cycle_is_silent_when_nothing_new(capsys):
    log_cycle([])

    assert capsys.readouterr().out == ""


def test_log_cycle_prints_new_event_subjects(capsys):
    log_cycle([{"subject": "aistack/aistack-core"}])

    out = capsys.readouterr().out
    assert "new=1" in out
    assert "aistack/aistack-core" in out


def test_log_cycle_always_prints_a_labelled_line(capsys):
    log_cycle([], label="stopping")

    assert "stopping" in capsys.readouterr().out


def test_run_cycle_first_run_has_no_backfill(tmp_path: Path):
    """
    No checkpoint yet: `since` defaults to `now`, never backfilling
    further back — `run_cycle`'s own docstring names the reason
    (`ARC-P-006`).
    """
    output_path = tmp_path / "docker-events" / "docker-events.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    now = datetime(2026, 9, 28, 10, 0, 0, tzinfo=timezone.utc)

    with _docker_events(stdout="") as mocked:
        run_cycle(output_path, checkpoint_path, dry_run=False, now=now)

    since_arg = mocked.call_args[0][0][mocked.call_args[0][0].index("--since") + 1]
    assert since_arg == now.isoformat()


def test_run_cycle_records_new_events_and_advances_the_checkpoint(tmp_path: Path):
    output_path = tmp_path / "docker-events" / "docker-events.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    now = datetime(2026, 9, 28, 10, 0, 10, tzinfo=timezone.utc)

    with _docker_events(stdout=ONE_EVENT_LINE):
        events = run_cycle(output_path, checkpoint_path, dry_run=False, now=now)

    assert len(events) == 1
    assert events[0]["subject"] == "some-container"
    assert output_path.exists()
    assert load_checkpoint(checkpoint_path) == now.isoformat()


def test_run_cycle_reuses_the_saved_checkpoint_as_the_next_since(tmp_path: Path):
    output_path = tmp_path / "docker-events" / "docker-events.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    save_checkpoint(checkpoint_path, "2026-09-28T09:00:00+00:00")
    now = datetime(2026, 9, 28, 10, 0, 0, tzinfo=timezone.utc)

    with _docker_events(stdout="") as mocked:
        run_cycle(output_path, checkpoint_path, dry_run=False, now=now)

    since_arg = mocked.call_args[0][0][mocked.call_args[0][0].index("--since") + 1]
    assert since_arg == "2026-09-28T09:00:00+00:00"


def test_dry_run_writes_nothing_and_does_not_advance_the_checkpoint(tmp_path: Path):
    output_path = tmp_path / "docker-events" / "docker-events.json"
    checkpoint_path = tmp_path / "checkpoint.json"
    now = datetime(2026, 9, 28, 10, 0, 0, tzinfo=timezone.utc)

    with _docker_events(stdout=ONE_EVENT_LINE):
        events = run_cycle(output_path, checkpoint_path, dry_run=True, now=now)

    assert len(events) == 1
    assert not output_path.exists()
    assert load_checkpoint(checkpoint_path) is None
