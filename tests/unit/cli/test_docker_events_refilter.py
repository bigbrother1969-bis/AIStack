from __future__ import annotations

import json
from pathlib import Path

import pytest

from aistack.cli.docker_events_refilter import USAGE, parse, refilter
from aistack.providers.docker.events import ExecNoiseFilter
from aistack.providers.docker.packages import DPKG_QUERY_COMMAND

PROBE = "exec_create: " + " ".join(DPKG_QUERY_COMMAND)


def _event(action: str, *, exec_id: str = "e1") -> dict:
    raw = {
        "Type": "container",
        "Action": action,
        "Actor": {"ID": "gone", "Attributes": {"execID": exec_id, "name": "x"}},
    }
    return {"subject": "x", "occurred_at": "2026-10-01T00:00:00+00:00", "action": action, "raw": raw}


def _write_batch(history: Path, name: str, events: list[dict]) -> None:
    history.mkdir(parents=True, exist_ok=True)
    (history / name).write_text(
        json.dumps({"since": "a", "until": "b", "events": events}), encoding="utf-8"
    )


def _offline_filter(**kwargs) -> ExecNoiseFilter:
    """A filter whose Docker lookups always come back empty — no daemon in a test."""

    noise = ExecNoiseFilter(remember_uninspectable=True, **kwargs)
    noise._healthcheck_commands = lambda container_id: frozenset()  # type: ignore[method-assign]
    return noise


def _history(tmp_path: Path) -> Path:
    return tmp_path / "docker-events" / "history" / "docker-events"


def test_parse_defaults_to_a_dated_archive_name():
    generated_dir, archive_name, dry_run = parse([])
    assert generated_dir == Path("reports/generated")
    assert archive_name.startswith("unfiltered-")
    assert dry_run is False


def test_usage_names_every_flag_parse_accepts():
    for flag in ("--generated-dir", "--archive-name", "--dry-run"):
        assert flag in USAGE


def test_noise_is_archived_and_only_kept_events_are_written_back(tmp_path: Path):
    history = _history(tmp_path)
    _write_batch(history, "2026-10-01T00-00-00Z.json", [_event(PROBE), _event("exec_die")])
    _write_batch(
        history,
        "2026-10-01T00-00-10Z.json",
        [_event(PROBE, exec_id="e2"), _event("start", exec_id="")],
    )

    summary = refilter(tmp_path, "unfiltered-test", dry_run=False, noise_filter=_offline_filter())

    archive = tmp_path / "docker-events" / "archive" / "unfiltered-test" / "docker-events"
    assert sorted(p.name for p in archive.iterdir()) == [
        "2026-10-01T00-00-00Z.json",
        "2026-10-01T00-00-10Z.json",
    ]
    assert [p.name for p in history.iterdir()] == ["2026-10-01T00-00-10Z.json"]
    kept = json.loads((history / "2026-10-01T00-00-10Z.json").read_text())
    assert [e["action"] for e in kept["events"]] == ["start"]
    assert summary.events_read == 4
    assert summary.events_kept == 1
    assert summary.files_written == 1


def test_an_old_container_s_healthcheck_is_matched_through_its_current_subject(tmp_path: Path):
    history = _history(tmp_path)
    _write_batch(history, "2026-10-01T00-00-00Z.json", [_event("exec_create: /bin/sh -c /hc.sh")])

    noise = _offline_filter(healthchecks_by_subject={"x": frozenset({"/bin/sh -c /hc.sh"})})
    summary = refilter(tmp_path, "a", dry_run=False, noise_filter=noise)

    assert summary.events_kept == 0
    assert list(history.iterdir()) == []


def test_dry_run_moves_and_writes_nothing(tmp_path: Path):
    history = _history(tmp_path)
    _write_batch(history, "2026-10-01T00-00-00Z.json", [_event(PROBE)])

    summary = refilter(tmp_path, "a", dry_run=True, noise_filter=_offline_filter())

    assert summary.events_read == 1 and summary.events_kept == 0
    assert (history / "2026-10-01T00-00-00Z.json").exists()
    assert not (tmp_path / "docker-events" / "archive").exists()


def test_an_existing_archive_is_never_overwritten(tmp_path: Path):
    _write_batch(_history(tmp_path), "2026-10-01T00-00-00Z.json", [_event(PROBE)])
    (tmp_path / "docker-events" / "archive" / "a" / "docker-events").mkdir(parents=True)

    with pytest.raises(SystemExit):
        refilter(tmp_path, "a", dry_run=False, noise_filter=_offline_filter())
