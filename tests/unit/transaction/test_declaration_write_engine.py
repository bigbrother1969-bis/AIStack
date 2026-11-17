from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from aistack.transaction.contracts.declaration_write import DeclarationWrite
from aistack.transaction.engines.declaration_write import DeclarationWriteEngine

MOMENT = datetime(2026, 11, 17, 19, 0, 5, tzinfo=timezone.utc)


def _engine() -> DeclarationWriteEngine:
    return DeclarationWriteEngine(clock=lambda: MOMENT)


def _payload(path: Path, content: str) -> DeclarationWrite:
    return DeclarationWrite(path=path, content=content, author="Fabrice", reason="test")


def test_a_new_file_is_written_without_a_copy(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "a.yml"

    result = _engine().execute(_payload(path, "one\n"))

    assert isinstance(result, dict)
    assert path.read_text(encoding="utf-8") == "one\n"
    assert result["changed"] is True
    assert result["copy"] == ""
    assert result["before"] == ""
    assert len(str(result["after"])) == 64


def test_a_changed_file_is_kept_beside_it_first(tmp_path: Path) -> None:
    path = tmp_path / "a.yml"
    path.write_text("old\n", encoding="utf-8")

    result = _engine().execute(_payload(path, "new\n"))

    assert isinstance(result, dict)
    kept = tmp_path / "a.yml.avant-20261117-190005"
    assert result["copy"] == str(kept)
    assert kept.read_text(encoding="utf-8") == "old\n"
    assert path.read_text(encoding="utf-8") == "new\n"
    assert result["before"] != result["after"]


def test_two_changes_in_the_same_second_keep_both_copies(tmp_path: Path) -> None:
    path = tmp_path / "a.yml"
    path.write_text("1\n", encoding="utf-8")

    _engine().execute(_payload(path, "2\n"))
    _engine().execute(_payload(path, "3\n"))

    assert (tmp_path / "a.yml.avant-20261117-190005").read_text(
        encoding="utf-8"
    ) == "1\n"
    assert (tmp_path / "a.yml.avant-20261117-190005-1").read_text(
        encoding="utf-8"
    ) == "2\n"


def test_the_same_content_writes_nothing(tmp_path: Path) -> None:
    path = tmp_path / "a.yml"
    path.write_text("same\n", encoding="utf-8")

    result = _engine().execute(_payload(path, "same\n"))

    assert isinstance(result, dict)
    assert result["changed"] is False
    assert result["copy"] == ""
    assert sorted(p.name for p in tmp_path.iterdir()) == ["a.yml"]


def test_the_file_mode_is_kept(tmp_path: Path) -> None:
    path = tmp_path / "a.yml"
    path.write_text("old\n", encoding="utf-8")
    path.chmod(0o640)

    _engine().execute(_payload(path, "new\n"))

    assert path.stat().st_mode & 0o777 == 0o640


def test_no_temporary_file_is_left_when_the_move_fails(tmp_path: Path) -> None:
    path = tmp_path / "a.yml"
    path.mkdir()

    with pytest.raises(OSError):
        _engine().execute(_payload(path, "x\n"))

    assert [p.name for p in tmp_path.iterdir()] == ["a.yml"]


def test_another_payload_is_refused() -> None:
    with pytest.raises(TypeError):
        _engine().execute("not a declaration")
