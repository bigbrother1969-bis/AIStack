from __future__ import annotations

import json
from pathlib import Path

from aistack.providers.docker.events_history import record_docker_events


def test_no_events_writes_nothing(tmp_path: Path):
    output_path = tmp_path / "docker-events" / "docker-events.json"

    result = record_docker_events(
        [], since="2026-09-28T10:00:00Z", until="2026-09-28T10:00:10Z", output_path=output_path
    )

    assert result is None
    assert not output_path.exists()


def test_new_events_are_written_to_the_stable_path_and_to_history(tmp_path: Path):
    output_path = tmp_path / "docker-events" / "docker-events.json"
    events = [
        {"subject": "aistack/aistack-core", "occurred_at": "2026-09-28T10:00:05Z", "action": "start", "raw": {}}
    ]

    result = record_docker_events(
        events, since="2026-09-28T10:00:00Z", until="2026-09-28T10:00:10Z", output_path=output_path
    )

    assert result == output_path
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["since"] == "2026-09-28T10:00:00Z"
    assert written["until"] == "2026-09-28T10:00:10Z"
    assert written["events"] == events

    history_dir = output_path.parent / "history" / "docker-events"
    assert len(list(history_dir.glob("*.json"))) == 1


def test_content_carries_no_collected_at_field(tmp_path: Path):
    """
    `aistack.priority.decision_history.serialize_decision`'s own
    lesson: the history filename `write_artifact_with_history` stamps
    already states the recording instant, so a second field inside the
    content could only repeat or drift from it.
    """
    output_path = tmp_path / "docker-events" / "docker-events.json"
    events = [{"subject": "x", "occurred_at": "2026-09-28T10:00:05Z", "action": "start", "raw": {}}]

    record_docker_events(events, since="S", until="U", output_path=output_path)

    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert "collected_at" not in written
