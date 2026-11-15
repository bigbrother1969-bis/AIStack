from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aistack.contracts.restart_loop import RestartLoop
from aistack.providers.docker.events_history import read_recent_docker_events
from aistack.runtime.restart_loop import (
    evaluate_restart_loops,
    find_restart_loops,
    restart_loop_findings,
)

NOW = datetime(2026, 10, 2, 20, 0, 0, tzinfo=timezone.utc)


def _die(subject: str, minutes_ago: float, action: str = "die") -> dict:
    return {
        "subject": subject,
        "action": action,
        "occurred_at": (NOW - timedelta(minutes=minutes_ago)).isoformat(),
    }


def test_a_restart_loop_cannot_be_below_its_own_threshold():
    with pytest.raises(ValueError):
        RestartLoop(container="x", restarts=4, window_minutes=60, threshold=5)
    with pytest.raises(ValueError):
        RestartLoop(container=" ", restarts=9, window_minutes=60, threshold=5)


def test_deaths_within_the_window_at_or_above_threshold_are_a_loop():
    events = [_die("arrstack/mularr", m) for m in range(5)] + [_die("other", 1)]
    loops = find_restart_loops(events, NOW, window_minutes=60, threshold=5)
    assert loops == (
        RestartLoop(container="arrstack/mularr", restarts=5, window_minutes=60, threshold=5),
    )


def test_old_deaths_starts_and_unreadable_instants_are_not_counted():
    events = (
        [_die("a", 61 + m) for m in range(10)]
        + [_die("a", m, action="start") for m in range(10)]
        + [{"subject": "a", "action": "die", "occurred_at": "not a date"}] * 10
        + [_die("a", 1)] * 4
    )
    assert find_restart_loops(events, NOW, window_minutes=60, threshold=5) == ()


def _die_in(subject: str, minutes_ago: float, *, one_off: str | None) -> dict:
    attributes = {} if one_off is None else {"com.docker.compose.oneoff": one_off}
    event = _die(subject, minutes_ago)
    event["raw"] = {"Actor": {"Attributes": attributes}}
    return event


def test_the_deaths_of_one_off_containers_are_not_crashes():
    # Ten `docker compose run --rm` commands in an hour: not a loop.
    runs = [_die_in("aistack/web", m, one_off="True") for m in range(10)]
    assert find_restart_loops(runs, NOW, window_minutes=60, threshold=5) == ()


def test_a_service_that_really_dies_is_still_a_loop_beside_one_off_runs():
    deaths = [_die_in("aistack/web", m, one_off="False") for m in range(5)]
    deaths += [_die_in("aistack/web", m, one_off="True") for m in range(10)]
    deaths += [_die("aistack/web", 30)]  # an event with no label at all
    (loop,) = find_restart_loops(deaths, NOW, window_minutes=60, threshold=5)
    assert loop.restarts == 6


def test_a_loop_becomes_an_ops_0004_finding_citing_it():
    loop = RestartLoop(container="arrstack/mularr", restarts=216, window_minutes=60, threshold=5)
    (finding,) = evaluate_restart_loops([loop])
    assert finding.subject == "arrstack/mularr"
    assert finding.signature == "OPS-0004"
    assert finding.evidence[0].reading == loop
    assert "docker logs mularr" in finding.remediation


def _batch(history: Path, instant: datetime, events: list[dict]) -> None:
    history.mkdir(parents=True, exist_ok=True)
    name = instant.strftime("%Y-%m-%dT%H-%M-%SZ") + ".json"
    (history / name).write_text(json.dumps({"since": "a", "until": "b", "events": events}))


def test_only_batches_written_since_the_cutoff_are_read(tmp_path: Path):
    output = tmp_path / "docker-events" / "docker-events.json"
    history = output.parent / "history" / "docker-events"
    _batch(history, NOW - timedelta(hours=3), [_die("old", 180)])
    _batch(history, NOW - timedelta(minutes=10), [_die("new", 10)])
    (history / "garbage.json").write_text("not json")

    events = read_recent_docker_events(NOW - timedelta(hours=1), output_path=output)

    assert [event["subject"] for event in events] == ["new"]


def test_no_history_at_all_means_no_finding(tmp_path: Path):
    output = tmp_path / "docker-events" / "docker-events.json"
    assert restart_loop_findings(NOW, events_output_path=output) == ()


def test_findings_end_to_end_from_recorded_batches(tmp_path: Path):
    output = tmp_path / "docker-events" / "docker-events.json"
    history = output.parent / "history" / "docker-events"
    _batch(history, NOW - timedelta(minutes=5), [_die("arrstack/mularr", m) for m in range(6)])

    findings = restart_loop_findings(NOW, events_output_path=output)

    assert [f.subject for f in findings] == ["arrstack/mularr"]
