"""`aistack.cli.security_assess` runs the Task through the Runtime and reports (ADR-0028 T1)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from aistack.cli import security_assess as cli
from aistack.security.exposure import ALL, Listener, Published


def _run(monkeypatch: pytest.MonkeyPatch, generated: Path, listeners, published) -> None:
    monkeypatch.setattr("aistack.tasks.security_assess.read_listeners", lambda: (listeners, []))
    monkeypatch.setattr("aistack.tasks.security_assess.read_published", lambda: published)
    monkeypatch.setattr("sys.argv", ["security_assess", str(generated)])
    cli.main()


def test_the_assessment_is_written_traced_and_told(tmp_path: Path, monkeypatch, capsys) -> None:
    _run(monkeypatch, tmp_path, [Listener("tcp", 9999, ALL)], [Published("web", "tcp", 9999, ALL)])

    out = capsys.readouterr().out
    assert "Security assessment: 0 urgent, 0 fix, 1 watch, 1 information" in out
    assert "9999/tcp (web)" in out and "not known:" in out

    report = json.loads((tmp_path / "security-assessment.json").read_text(encoding="utf-8"))["security"]
    assert report["listeners"] == [{"protocol": "tcp", "port": 9999, "bind": "all"}]
    assert report["published"][0]["container"] == "web"
    assert "security.assess" in (tmp_path / "execution-trace.json").read_text(encoding="utf-8")


def test_a_finding_to_fix_makes_the_command_exit_1(tmp_path: Path, monkeypatch, capsys) -> None:
    with pytest.raises(SystemExit) as stopped:
        _run(monkeypatch, tmp_path, [Listener("tcp", 2375, ALL)], [])

    assert stopped.value.code == 1
    assert "[fix]" in capsys.readouterr().out


def test_each_run_is_kept_in_the_history(tmp_path: Path, monkeypatch) -> None:
    _run(monkeypatch, tmp_path, [], [])
    _run(monkeypatch, tmp_path, [Listener("tcp", 9999, ALL)], [])

    history = list((tmp_path / "history" / "security-assessment").glob("*.json"))
    assert len(history) == 2


def test_propose_prints_only_the_block_and_applies_nothing(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr("aistack.tasks.security_assess.read_listeners", lambda: ([Listener("tcp", 9999, ALL)], []))
    monkeypatch.setattr("aistack.tasks.security_assess.read_published", lambda: [Published("web", "tcp", 9999, ALL)])
    monkeypatch.setattr("sys.argv", ["security_assess", "--propose", str(tmp_path)])

    cli.main()

    assert capsys.readouterr().out == "declared_ports:\n  9999: web\n"
