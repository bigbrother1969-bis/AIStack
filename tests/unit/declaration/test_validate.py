"""`aistack.declaration.validate`: which declarations their own loader does not read (ADR-0027 § 12)."""

from __future__ import annotations

from pathlib import Path

import pytest

from aistack.api_keys import load_api_keys
from aistack.config import shipped_definitions
from aistack.declaration import observe, validate


def test_every_shipped_declaration_has_a_loader_and_nothing_else_has() -> None:
    assert set(validate.LOADERS) == {path.name for path in shipped_definitions()}


@pytest.mark.parametrize("source", shipped_definitions(), ids=lambda path: path.name)
def test_every_shipped_declaration_is_read_by_its_loader(source: Path, tmp_path: Path) -> None:
    assert validate.problem(source.name, source, tmp_path) == ""


@pytest.mark.parametrize("source", shipped_definitions(), ids=lambda path: path.name)
def test_a_syntax_error_is_reported_by_every_loader(source: Path, tmp_path: Path) -> None:
    broken = tmp_path / source.name
    broken.write_text("a: [unclosed\n", encoding="utf-8")

    assert validate.problem(source.name, broken, tmp_path) != ""


def test_a_syntax_error_names_the_line(tmp_path: Path) -> None:
    broken = tmp_path / "hosts.yml"
    broken.write_text("a: 1\nb: [unclosed\n", encoding="utf-8")

    assert "line" in validate.problem("hosts.yml", broken, tmp_path)


def test_a_list_where_a_mapping_is_expected_is_reported(tmp_path: Path) -> None:
    keys = tmp_path / "api_keys.yml"
    keys.write_text("[1, 2]", encoding="utf-8")

    with pytest.raises(ValueError, match="not a mapping"):
        load_api_keys(keys)
    assert validate.problem("api_keys.yml", keys, tmp_path) != ""


def test_an_error_carries_the_loaders_words_and_stays_short(tmp_path: Path) -> None:
    broken = tmp_path / "hosts.yml"
    broken.write_text("x: [" + "y" * 2000, encoding="utf-8")

    assert len(validate.problem("hosts.yml", broken, tmp_path)) <= validate.MAX_ERROR


def test_a_name_that_is_not_a_declaration_is_not_judged(tmp_path: Path) -> None:
    other = tmp_path / "notes.txt"
    other.write_text("[", encoding="utf-8")

    assert validate.problem("notes.txt", other, tmp_path) == ""


def test_validate_lists_only_the_broken_files_and_writes_nothing(tmp_path: Path) -> None:
    shipped = shipped_definitions()
    config, generated = tmp_path / "config", tmp_path / "data"
    config.mkdir()
    (config / shipped[0].name).write_text("a: [unclosed\n", encoding="utf-8")
    (config / shipped[1].name).write_text(shipped[1].read_text(encoding="utf-8"), encoding="utf-8")

    invalid = validate.validate(config, generated, shipped)

    assert [item.name for item in invalid] == [shipped[0].name]
    assert not generated.exists()


def test_the_last_valid_copy_is_the_newest_one_the_loader_reads(tmp_path: Path) -> None:
    source = shipped_definitions()[0]
    generated = tmp_path / "data"
    seen = observe.seen_path(generated, source.name).parent
    seen.mkdir(parents=True)
    good = seen / f"{source.name}.avant-observe-20261117-100000"
    bad = seen / f"{source.name}.avant-observe-20261117-110000"
    good.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    bad.write_text("a: [unclosed\n", encoding="utf-8")

    assert validate.last_valid_copy(generated, source.name, seen) == str(good)
    assert validate.last_valid_copy(generated, "absent.yml", seen) == ""


def test_the_invalid_state_is_kept_even_when_empty_and_adds_no_history_when_unchanged(tmp_path: Path) -> None:
    generated = tmp_path / "data"
    seen = lambda name: observe.seen_path(generated, name).parent  # noqa: E731
    broken = [validate.Invalid("hosts.yml", "bad")]

    assert validate.record_invalid(generated, [], seen) == []
    assert validate.read_invalid(generated) == []
    validate.record_invalid(generated, broken, seen)
    validate.record_invalid(generated, broken, seen)
    validate.record_invalid(generated, [], seen)

    assert [item["name"] for item in validate.record_invalid(generated, broken, seen)] == ["hosts.yml"]
    assert validate.read_invalid(generated)[0]["error"] == "bad"
    assert len(list((generated / "history" / "declaration-invalid").glob("*.json"))) == 4


def test_an_unreadable_invalid_state_is_empty(tmp_path: Path) -> None:
    (tmp_path / validate.STATE).write_text("{", encoding="utf-8")

    assert validate.read_invalid(tmp_path) == []
