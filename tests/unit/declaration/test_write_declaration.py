from __future__ import annotations

import json
from pathlib import Path

import pytest

from aistack.declaration import DeclarationNotWritten, write_declaration
from aistack.kernel.bootstrap.default import create_kernel
from aistack.transaction.contracts.declaration_write import KIND


def _transactions():
    return create_kernel().services.transactions


def test_the_kernel_knows_the_operation() -> None:
    assert _transactions().registry.get(KIND) is not None


def test_a_change_is_written_and_recorded(tmp_path: Path) -> None:
    path = tmp_path / "decl" / "a.yml"
    path.parent.mkdir()
    path.write_text("old\n", encoding="utf-8")
    generated = tmp_path / "generated"

    result = write_declaration(
        _transactions(), generated, path, "new\n", "Fabrice", "because"
    )

    assert path.read_text(encoding="utf-8") == "new\n"
    record = json.loads(
        (generated / "declaration-change.json").read_text(encoding="utf-8")
    )
    assert record["author"] == "Fabrice"
    assert record["reason"] == "because"
    assert record["path"] == str(path)
    assert record["copy"] == result["copy"]
    assert "new" not in json.dumps(record).replace("changed", "")
    assert list((generated / "history").rglob("*.json"))


def test_nothing_changed_leaves_no_record(tmp_path: Path) -> None:
    path = tmp_path / "a.yml"
    path.write_text("same\n", encoding="utf-8")

    result = write_declaration(
        _transactions(), tmp_path / "generated", path, "same\n", "", "x"
    )

    assert result["changed"] is False
    assert not (tmp_path / "generated").exists()


def test_a_failed_write_says_so_and_leaves_no_record(tmp_path: Path) -> None:
    path = tmp_path / "a.yml"
    path.mkdir()

    with pytest.raises(DeclarationNotWritten) as raised:
        write_declaration(_transactions(), tmp_path / "generated", path, "x\n", "", "x")

    assert raised.value.path == path
    assert not (tmp_path / "generated").exists()
