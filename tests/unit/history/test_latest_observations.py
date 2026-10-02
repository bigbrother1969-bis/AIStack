from __future__ import annotations

from pathlib import Path

from aistack.history import available_instants, latest_observations, observation_at


def _touch(directory: Path, name: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text("{}", encoding="utf-8")


def test_latest_observations_matches_the_per_instant_walk_it_replaces(tmp_path: Path):
    history = tmp_path / "history" / "stream"
    for name in (
        "2026-10-01T00-00-10Z.json",
        "2026-10-01T00-00-00Z.json",
        "2026-10-01T00-00-00Z-1.json",
        "2026-10-01T00-00-00Z-2.json",
        "2026-10-01T00-00-20Z.json",
        "not-a-history-file.txt",
    ):
        _touch(history, name)

    expected = [
        observation_at(tmp_path, "stream", instant)
        for instant in available_instants(tmp_path, "stream")
    ]

    assert latest_observations(tmp_path, "stream") == expected
    assert [o.path.name for o in latest_observations(tmp_path, "stream")] == [
        "2026-10-01T00-00-00Z-2.json",
        "2026-10-01T00-00-10Z.json",
        "2026-10-01T00-00-20Z.json",
    ]


def test_latest_observations_of_a_missing_stream_is_empty(tmp_path: Path):
    assert latest_observations(tmp_path, "nothing") == []
