"""A shipped declaration that changes, and the host's copy (ADR-0017, 1.9)."""

from __future__ import annotations

from pathlib import Path

from aistack.instance.declarations import SEEN_RECORD, divergences, follow, mark_seen
from aistack.instance.first_start import remember_copies


def _shipped(tmp_path: Path, text: str) -> Path:
    source = tmp_path / "package" / "aistack" / "area" / "definitions" / "thing.yml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(text, encoding="utf-8")
    return source


def _config(tmp_path: Path, text: str, copied: bool) -> Path:
    directory = tmp_path / "config"
    directory.mkdir(exist_ok=True)
    (directory / "thing.yml").write_text(text, encoding="utf-8")
    if copied:
        remember_copies(directory, ["thing.yml"])
    return directory


def test_an_untouched_copy_follows_the_shipped_version(tmp_path: Path):
    directory = _config(tmp_path, "a: 1\n", copied=True)
    source = _shipped(tmp_path, "a: 1\nb: 2\n")

    assert follow(directory, [source]) == ["thing.yml"]
    assert (directory / "thing.yml").read_text(encoding="utf-8") == "a: 1\nb: 2\n"
    assert divergences(directory, [source]) == []
    # Still the shipped version: replaced again next time it changes.
    source.write_text("a: 1\nb: 3\n", encoding="utf-8")
    assert follow(directory, [source]) == ["thing.yml"]


def test_an_edited_copy_is_never_touched_but_its_change_is_reported(tmp_path: Path):
    directory = _config(tmp_path, "a: 1\n", copied=True)
    source = _shipped(tmp_path, "a: 1\n")
    follow(directory, [source])
    (directory / "thing.yml").write_text("a: 9\n", encoding="utf-8")

    source.write_text("a: 1\nb: 2\n", encoding="utf-8")
    assert follow(directory, [source]) == []
    assert (directory / "thing.yml").read_text(encoding="utf-8") == "a: 9\n"

    (divergence,) = divergences(directory, [source])
    assert divergence.name == "thing.yml"
    assert "-a: 9" in divergence.diff and "+b: 2" in divergence.diff

    assert mark_seen(directory, [source], "thing.yml")
    assert divergences(directory, [source]) == []
    assert not mark_seen(directory, [source], "other.yml")


def test_a_file_the_owner_put_there_is_reported_only_for_later_changes(tmp_path: Path):
    # GIGABYTE's own files, placed before the first start: never copied.
    directory = _config(tmp_path, "mine: true\n", copied=False)
    source = _shipped(tmp_path, "reference: true\n")

    assert follow(directory, [source]) == []
    assert divergences(directory, [source]) == []
    assert (directory / SEEN_RECORD).is_file()

    source.write_text("reference: true\nnew: 1\n", encoding="utf-8")
    follow(directory, [source])
    assert [d.name for d in divergences(directory, [source])] == ["thing.yml"]
    assert (directory / "thing.yml").read_text(encoding="utf-8") == "mine: true\n"


def test_a_file_that_already_equals_the_new_shipped_version_is_not_reported(tmp_path: Path):
    directory = _config(tmp_path, "x: 1\n", copied=False)
    source = _shipped(tmp_path, "x: 0\n")
    follow(directory, [source])
    source.write_text("x: 1\n", encoding="utf-8")

    assert divergences(directory, [source]) == []


def test_a_hand_made_copy_equal_to_the_shipped_version_follows_it(tmp_path: Path):
    # GIGABYTE, 2026-10-09: health_score_weights.yml copied by hand,
    # identical to the shipped file, never followed 2.0's new domain.
    directory = _config(tmp_path, "w: 1\n", copied=False)
    source = _shipped(tmp_path, "w: 1\n")
    assert follow(directory, [source]) == []

    source.write_text("w: 1\nhosts: 15\n", encoding="utf-8")
    assert follow(directory, [source]) == ["thing.yml"]
    assert (directory / "thing.yml").read_text(encoding="utf-8") == "w: 1\nhosts: 15\n"
    assert divergences(directory, [source]) == []
