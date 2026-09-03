from datetime import datetime, timezone
from pathlib import Path

from aistack.generators.history import write_artifact_with_history
from aistack.history.query import (
    available_instants,
    available_stems,
    format_instant,
    observation_at,
    parse_instant,
)


def _write(generated: Path, stem: str, content: str, at: datetime, monkeypatch) -> None:
    """
    Write one Observation History entry as though it had happened
    at `at`, by freezing `write_artifact_with_history`'s clock —
    the same technique `tests/unit/generators/test_history.py`
    uses for its same-second collision test, reused here so this
    module's tests build fixtures through the real writer rather
    than hand-crafting filenames the writer might stop producing.
    """

    import aistack.generators.history as history_module

    class FrozenDatetime(history_module.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(
                at.year, at.month, at.day, at.hour, at.minute, at.second, tzinfo=tz
            )

    monkeypatch.setattr(history_module, "datetime", FrozenDatetime)
    write_artifact_with_history(content, generated / f"{stem}.json")


def test_available_stems_lists_the_directories_history_was_written_under(
    tmp_path: Path, monkeypatch
):
    generated = tmp_path / "reports" / "generated"

    _write(generated, "docker-runtime-catalog", "a\n", datetime(2026, 9, 3, 9, tzinfo=timezone.utc), monkeypatch)
    _write(generated, "compose-runtime-catalog", "b\n", datetime(2026, 9, 3, 9, tzinfo=timezone.utc), monkeypatch)

    assert available_stems(generated) == [
        "compose-runtime-catalog",
        "docker-runtime-catalog",
    ]


def test_available_stems_is_empty_when_nothing_was_ever_observed(tmp_path: Path):
    assert available_stems(tmp_path / "reports" / "generated") == []


def test_available_instants_lists_every_write_oldest_first(tmp_path: Path, monkeypatch):
    generated = tmp_path / "reports" / "generated"
    stem = "docker-runtime-catalog"

    _write(generated, stem, "first\n", datetime(2026, 9, 3, 9, 0, 0, tzinfo=timezone.utc), monkeypatch)
    _write(generated, stem, "second\n", datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc), monkeypatch)
    _write(generated, stem, "third\n", datetime(2026, 9, 3, 8, 0, 0, tzinfo=timezone.utc), monkeypatch)

    assert available_instants(generated, stem) == [
        datetime(2026, 9, 3, 8, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 3, 9, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc),
    ]


def test_available_instants_is_empty_for_an_unobserved_stem(tmp_path: Path):
    generated = tmp_path / "reports" / "generated"
    assert available_instants(generated, "never-written") == []


def test_observation_at_returns_the_most_recent_write_at_or_before(
    tmp_path: Path, monkeypatch
):
    generated = tmp_path / "reports" / "generated"
    stem = "docker-runtime-catalog"

    _write(generated, stem, "at-nine\n", datetime(2026, 9, 3, 9, 0, 0, tzinfo=timezone.utc), monkeypatch)
    _write(generated, stem, "at-noon\n", datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc), monkeypatch)

    result = observation_at(generated, stem, datetime(2026, 9, 3, 13, 0, 0, tzinfo=timezone.utc))

    assert result is not None
    assert result.observed_at == datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)
    assert result.read() == "at-noon\n"


def test_observation_at_falls_back_to_an_earlier_write_when_asked_between_two(
    tmp_path: Path, monkeypatch
):
    generated = tmp_path / "reports" / "generated"
    stem = "docker-runtime-catalog"

    _write(generated, stem, "at-nine\n", datetime(2026, 9, 3, 9, 0, 0, tzinfo=timezone.utc), monkeypatch)
    _write(generated, stem, "at-noon\n", datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc), monkeypatch)

    result = observation_at(generated, stem, datetime(2026, 9, 3, 10, 0, 0, tzinfo=timezone.utc))

    assert result is not None
    assert result.observed_at == datetime(2026, 9, 3, 9, 0, 0, tzinfo=timezone.utc)
    assert result.read() == "at-nine\n"


def test_observation_at_returns_none_when_asked_before_the_first_observation(
    tmp_path: Path, monkeypatch
):
    generated = tmp_path / "reports" / "generated"
    stem = "docker-runtime-catalog"

    _write(generated, stem, "at-noon\n", datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc), monkeypatch)

    result = observation_at(generated, stem, datetime(2026, 9, 3, 8, 0, 0, tzinfo=timezone.utc))

    assert result is None


def test_observation_at_returns_none_for_a_stem_with_no_history(tmp_path: Path):
    generated = tmp_path / "reports" / "generated"

    result = observation_at(generated, "never-written", datetime.now(timezone.utc))

    assert result is None


def test_observation_at_breaks_same_second_ties_by_keeping_the_last_write(
    tmp_path: Path, monkeypatch
):
    """
    `write_artifact_with_history`'s collision suffix keeps two
    same-second writes both on disk. Reconstructing "what did it
    know at that instant" must resolve to what was actually
    current a moment later — the last one written — not an
    arbitrary one of the two.
    """

    generated = tmp_path / "reports" / "generated"
    stem = "docker-runtime-catalog"
    instant = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)

    _write(generated, stem, "first\n", instant, monkeypatch)
    _write(generated, stem, "second\n", instant, monkeypatch)
    _write(generated, stem, "third\n", instant, monkeypatch)

    result = observation_at(generated, stem, instant)

    assert result is not None
    assert result.observed_at == instant
    assert result.read() == "third\n"


def test_observation_at_treats_a_naive_instant_as_utc(tmp_path: Path, monkeypatch):
    generated = tmp_path / "reports" / "generated"
    stem = "docker-runtime-catalog"

    _write(generated, stem, "content\n", datetime(2026, 9, 3, 9, 0, 0, tzinfo=timezone.utc), monkeypatch)

    result = observation_at(generated, stem, datetime(2026, 9, 3, 10, 0, 0))

    assert result is not None
    assert result.read() == "content\n"


def test_format_and_parse_instant_round_trip():
    instant = datetime(2026, 9, 3, 18, 5, 0, tzinfo=timezone.utc)

    assert parse_instant(format_instant(instant)) == instant


def test_parse_instant_rejects_a_shape_it_did_not_write():
    try:
        parse_instant("2026-09-03T18:05:00Z")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "2026-09-03T18-05-00Z" in str(exc)
