"""`aistack-firewall-snapshot` writes what the host's firewall says, dated, and nothing else (ADR-0028)."""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

import pytest

from aistack import firewall_snapshot as snapshot


def _answers(monkeypatch: pytest.MonkeyPatch, outputs: dict[str, str | None]) -> None:
    def run(command, **_):
        text = outputs[command[0]]
        return subprocess.CompletedProcess(command, 0 if text else 1, stdout=text or "")

    monkeypatch.setattr(snapshot.subprocess, "run", run)
    monkeypatch.setattr(snapshot.os, "chown", lambda *_: None)


def _main(monkeypatch: pytest.MonkeyPatch, output: Path) -> int:
    monkeypatch.setattr(sys, "argv", ["aistack-firewall-snapshot", "--output", str(output)])
    return snapshot.main()


def test_each_answer_is_written_under_a_dated_first_line(tmp_path: Path, monkeypatch) -> None:
    _answers(monkeypatch, {"iptables-save": "*filter\nCOMMIT\n", "ip6tables-save": "*filter\nCOMMIT\n"})

    assert _main(monkeypatch, tmp_path) == 0

    for name in ("firewall-iptables.txt", "firewall-ip6tables.txt"):
        lines = (tmp_path / name).read_text(encoding="utf-8").splitlines()
        assert lines[0].startswith(snapshot.HEADER) and lines[1:] == ["*filter", "COMMIT"]


def test_a_command_that_fails_removes_its_old_file(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "firewall-ip6tables.txt").write_text("old", encoding="utf-8")
    _answers(monkeypatch, {"iptables-save": "*filter\nCOMMIT\n", "ip6tables-save": None})

    assert _main(monkeypatch, tmp_path) == 0
    assert not (tmp_path / "firewall-ip6tables.txt").exists()


def test_a_missing_ipv4_answer_is_a_failure(tmp_path: Path, monkeypatch) -> None:
    _answers(monkeypatch, {"iptables-save": None, "ip6tables-save": None})

    assert _main(monkeypatch, tmp_path) == 1


def test_the_script_uses_the_standard_library_only() -> None:
    tree = ast.parse(Path(snapshot.__file__).read_text(encoding="utf-8"))
    imported = {
        (node.module or "").split(".")[0] if isinstance(node, ast.ImportFrom) else alias.name.split(".")[0]
        for node in ast.walk(tree)
        for alias in (node.names if isinstance(node, (ast.Import, ast.ImportFrom)) else [])
    }

    assert imported <= set(sys.stdlib_module_names)
