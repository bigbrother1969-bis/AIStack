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
    name = shipped_definitions()[0].name
    (config / name).write_text("a: 1\n", encoding="utf-8")

    _run(monkeypatch, config, generated)
    assert "1 new reference(s)" in capsys.readouterr().out

    (config / name).write_text("a: 2\n", encoding="utf-8")
    _run(monkeypatch, config, generated)

    out = capsys.readouterr().out
    assert "1 edited by hand" in out and name in out
    record = json.loads((generated / "declaration-observed.json").read_text(encoding="utf-8"))
    assert record["name"] == name
    trace = (generated / "execution-trace.json").read_text(encoding="utf-8")
    assert "declarations.observe" in trace
    assert "a: 2" not in trace


def test_without_a_configuration_directory_there_is_nothing_to_observe(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv(CONFIG_DIR_ENV, raising=False)
    monkeypatch.setattr("sys.argv", ["declarations_observe", str(tmp_path / "data")])

    cli.main()

    assert "nothing to observe" in capsys.readouterr().out
    assert not (tmp_path / "data" / "declarations").exists()
