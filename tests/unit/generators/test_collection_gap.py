from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from aistack.generators.collection_gap import record_collection_gap


def test_first_run_writes_nothing(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    now = datetime(2026, 9, 28, 10, 0, 0, tzinfo=timezone.utc)

    result = record_collection_gap(
        "docker-events", checkpoint_until=None, now=now, generated_dir=generated_dir
    )

    assert result is None
    assert not (generated_dir / "collection-gaps").exists()


def test_a_real_gap_is_recorded_to_the_stream_s_own_root(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    now = datetime(2026, 9, 28, 10, 5, 0, tzinfo=timezone.utc)

    result = record_collection_gap(
        "docker-events",
        checkpoint_until="2026-09-28T10:00:00+00:00",
        now=now,
        generated_dir=generated_dir,
    )

    expected_path = generated_dir / "collection-gaps" / "docker-events" / "collection-gap.json"
    assert result == expected_path
    written = json.loads(expected_path.read_text(encoding="utf-8"))
    assert written == {"stream": "docker-events", "start": "2026-09-28T10:00:00+00:00"}

    history_dir = expected_path.parent / "history" / "collection-gap"
    assert len(list(history_dir.glob("*.json"))) == 1


def test_content_carries_no_end_field(tmp_path: Path):
    """
    `record_collection_gap`'s own docstring: the history filename
    already states the recording instant, which is also the gap's own
    end — a second field inside the content could only repeat or
    drift from it, the same restraint `events_history`'s own
    `collected_at` docstring already gives.
    """

    generated_dir = tmp_path / "reports" / "generated"
    now = datetime(2026, 9, 28, 10, 5, 0, tzinfo=timezone.utc)

    record_collection_gap(
        "docker-events",
        checkpoint_until="2026-09-28T10:00:00+00:00",
        now=now,
        generated_dir=generated_dir,
    )

    written_path = generated_dir / "collection-gaps" / "docker-events" / "collection-gap.json"
    written = json.loads(written_path.read_text(encoding="utf-8"))
    assert "end" not in written


def test_no_real_gap_writes_nothing(tmp_path: Path):
    """Defensive: `now` at or before the checkpoint is not expected in
    normal operation, but must not raise or fabricate a negative gap."""

    generated_dir = tmp_path / "reports" / "generated"
    now = datetime(2026, 9, 28, 10, 0, 0, tzinfo=timezone.utc)

    result = record_collection_gap(
        "docker-events",
        checkpoint_until="2026-09-28T10:00:00+00:00",
        now=now,
        generated_dir=generated_dir,
    )

    assert result is None
    assert not (generated_dir / "collection-gaps").exists()


def test_two_streams_get_two_independent_roots(tmp_path: Path):
    generated_dir = tmp_path / "reports" / "generated"
    now = datetime(2026, 9, 28, 10, 5, 0, tzinfo=timezone.utc)

    record_collection_gap(
        "docker-events", checkpoint_until="2026-09-28T10:00:00+00:00", now=now, generated_dir=generated_dir
    )
    record_collection_gap(
        "docker-diff", checkpoint_until="2026-09-28T09:50:00+00:00", now=now, generated_dir=generated_dir
    )

    assert (generated_dir / "collection-gaps" / "docker-events" / "collection-gap.json").exists()
    assert (generated_dir / "collection-gaps" / "docker-diff" / "collection-gap.json").exists()
