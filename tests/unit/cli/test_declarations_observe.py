"""`aistack.cli.declarations_observe` runs the Task through the Runtime and records what it saw."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aistack.cli import declarations_observe as cli
from aistack.config import CONFIG_DIR_ENV, shipped_definitions


def _run(monkeypatch: pytest.MonkeyPatch, config: Path, generated: Path) -> None:
    monkeypatch.setenv(CONFIG_DIR_ENV, str(config))
    monkeypatch.setattr("sys.argv", ["declarations_observe", str(generated)])
    cli.main()


def test_a_hand_edit_is_seen_recorded_and_traced(tmp_path: Path, monkeypatch, capsys) -> None:
    config = tmp_path / "config"
    config.mkdir()
    generated = tmp_path / "data"
    shipped = shipped_definitions()[0]
    name = shipped.name
    text = shipped.read_text(encoding="utf-8")
    (config / name).write_text(text, encoding="utf-8")

    _run(monkeypatch, config, generated)
    assert "1 new reference(s)" in capsys.readouterr().out

    (config / name).write_text(text + "# a hand edit\n", encoding="utf-8")
    _run(monkeypatch, config, generated)

    out = capsys.readouterr().out
    assert "1 edited by hand" in out and name in out
    record = json.loads((generated / "declaration-observed.json").read_text(encoding="utf-8"))
    assert record["name"] == name
    trace = (generated / "execution-trace.json").read_text(encoding="utf-8")
    assert "declarations.observe" in trace
    assert "a hand edit" not in trace


def test_without_a_configuration_directory_there_is_nothing_to_observe(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)
    monkeypatch.setattr("sys.argv", ["declarations_observe", str(tmp_path / "data")])

    cli.main()

    assert "nothing to observe" in capsys.readouterr().out
    assert not (tmp_path / "data" / "declarations").exists()


def test_an_invalid_declaration_is_reported_with_the_last_valid_copy_and_the_pass_fails(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    config = tmp_path / "config"
    config.mkdir()
    generated = tmp_path / "data"
    shipped = shipped_definitions()[0]
    (config / shipped.name).write_text(shipped.read_text(encoding="utf-8"), encoding="utf-8")
    _run(monkeypatch, config, generated)
    capsys.readouterr()

    (config / shipped.name).write_text("a: [unclosed\n", encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        _run(monkeypatch, config, generated)

    out = capsys.readouterr().out
    assert stop.value.code == 1
    assert f"! {shipped.name} is not read by its loader" in out
    assert f"{shipped.name}.avant-observe-" in out
    record = json.loads((generated / "declaration-observed.json").read_text(encoding="utf-8"))
    assert record["valid"] is False and record["error"] and record["last_valid_copy"]
    state = json.loads((generated / "declaration-invalid.json").read_text(encoding="utf-8"))
    assert [item["name"] for item in state["invalid"]] == [shipped.name]

    (config / shipped.name).write_text(shipped.read_text(encoding="utf-8"), encoding="utf-8")
    _run(monkeypatch, config, generated)
    assert json.loads((generated / "declaration-invalid.json").read_text(encoding="utf-8")) == {"invalid": []}
    assert "unclosed" not in json.dumps(record)
