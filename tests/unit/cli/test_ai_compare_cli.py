from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aistack.cli import ai_compare
from aistack.tasks import ai_compare as task
from tests.unit.troubleshooting.test_ask_local import CHAT_REPLY, OLLAMA_REPLY, dead_port, serve

REPORT = {
    "collected_at": "2026-11-20T10:00:00+00:00",
    "measures": {},
    "findings": [
        {"key": "drift.gigabyte.sensitive", "severity": "watch", "title": "gigabyte: 2 sensitive change(s)", "evidence": ["added /usr/local/sbin/aistack-host-hygiene"], "unknown": "Who made the change"},
        {"key": "host.msi.updates", "severity": "fix", "title": "msi: updates waiting", "evidence": ["12 packages"], "unknown": ""},
        {"key": "exposure.msi.fine", "severity": "information", "title": "quiet", "evidence": [], "unknown": ""},
    ],
}


@pytest.fixture
def generated(tmp_path: Path) -> Path:
    (tmp_path / "security-assessment.json").write_text(json.dumps({"security": REPORT}), encoding="utf-8")
    return tmp_path


@pytest.fixture
def servers():
    made: list[Any] = []

    def start(reply: dict[str, object]):
        httpd, calls = serve(reply)
        made.append(httpd)
        return httpd.server_address[1], calls

    yield start
    for httpd in made:
        httpd.shutdown()
        httpd.server_close()


def test_the_engines_are_compared_on_the_worst_findings_and_a_report_is_written(generated: Path, servers, capsys):
    chat_port, chat_calls = servers(CHAT_REPLY)
    ollama_port, ollama_calls = servers(OLLAMA_REPLY)

    code = ai_compare.main(
        [
            "--generated", str(generated),
            "--engine", f"openai_chat@127.0.0.1:{chat_port}/olala?effort=low&label=Olala",
            "--engine", f"ollama@127.0.0.1:{ollama_port}/qwen",
            "--max", "1",
            "--operations", "reason,explain",
        ]
    )

    assert code == 0
    reports = list((generated / "ai-compare").glob("compare.md"))
    assert len(reports) == 1 and list((generated / "ai-compare" / "history" / "compare").glob("*.md"))
    text = reports[0].read_text(encoding="utf-8")
    assert "## host.msi.updates" in text and "drift.gigabyte" not in text  # the worst one only
    assert "from olala" in text and "from ollama" in text and "Olala (low)" in text
    assert len(chat_calls) == 2 and len(ollama_calls) == 2  # two operations each, nothing more
    assert "Report:" in capsys.readouterr().out


def test_a_dry_run_sends_nothing_and_writes_nothing(generated: Path, servers, capsys):
    port, calls = servers(OLLAMA_REPLY)

    code = ai_compare.main(["--generated", str(generated), "--engine", f"ollama@127.0.0.1:{port}/qwen", "--finding", "drift.gigabyte.sensitive", "--dry-run"])

    assert code == 0 and calls == [] and not (generated / "ai-compare").exists()
    assert "drift.gigabyte.sensitive" in capsys.readouterr().out


def test_a_silent_engine_is_reported_not_raised(generated: Path):
    code = ai_compare.main(["--generated", str(generated), "--engine", f"ollama@127.0.0.1:{dead_port()}/qwen?timeout=2", "--max", "1", "--operations", "reason"])

    assert code == 0
    text = (generated / "ai-compare" / "compare.md").read_text(encoding="utf-8")
    assert "*Pas de réponse :" in text and "could not be reached" in text


@pytest.mark.parametrize(
    "extra, message",
    [
        (["--engine", "nonsense"], "expected kind@host:port/model"),
        (["--engine", "ollama@h:1/m", "--finding", "no.such.key"], "no finding 'no.such.key'"),
        (["--engine", "ollama@h:1/m", "--operations", "guess"], "unknown operation"),
    ],
)
def test_a_wrong_request_is_refused_with_code_2(generated: Path, capsys, extra: list[str], message: str):
    assert ai_compare.main(["--generated", str(generated), *extra]) == 2
    assert message in capsys.readouterr().err


def test_without_a_report_or_without_an_engine_it_stops(tmp_path: Path, generated: Path, capsys, monkeypatch: pytest.MonkeyPatch):
    assert ai_compare.main(["--generated", str(tmp_path / "nowhere"), "--engine", "ollama@h:1/m"]) == 2
    assert "no readable security report" in capsys.readouterr().err

    empty = tmp_path / "ai_runtime.yml"
    empty.write_text("host: h\nport: 1\n", encoding="utf-8")
    monkeypatch.setattr(task, "AI_RUNTIME", empty)
    assert ai_compare.main(["--generated", str(generated)]) == 2
    assert "no engine to compare" in capsys.readouterr().err


def test_the_declared_engines_are_compared_when_none_is_given(generated: Path, servers, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    port, calls = servers(OLLAMA_REPLY)
    declared = tmp_path / "ai_runtime.yml"
    declared.write_text(f"host: 127.0.0.1\nport: {port}\nmodel: qwen\n", encoding="utf-8")
    monkeypatch.setattr(task, "AI_RUNTIME", declared)

    assert ai_compare.main(["--generated", str(generated), "--max", "1", "--operations", "reason"]) == 0
    assert len(calls) == 1
