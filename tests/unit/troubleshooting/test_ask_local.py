from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from aistack.ai_runtime.definition import AIRuntimeDefinition, LocalEngineDefinition
from aistack.contracts.runtime_finding import MatchedLine, RuntimeFinding
from aistack.contracts.runtime_observation import LogEntry
from aistack.troubleshooting import guide


def finding() -> RuntimeFinding:
    return RuntimeFinding(subject="security:k", signature="ADR-0028/other", interpretation="i", remediation="r", confidence="watch", grounding="test", evidence=(MatchedLine(LogEntry(offset=0, text="a line")),))


def serve(reply: dict[str, object]):
    calls: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            calls.append(self.path)
            payload = json.dumps(reply).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, calls


@pytest.fixture
def servers():
    made = []

    def start(reply):
        httpd, calls = serve(reply)
        made.append(httpd)
        return httpd.server_address[1], calls

    yield start
    for httpd in made:
        httpd.shutdown()
        httpd.server_close()


def dead_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def ollama(port: int, model: str = "qwen", **kwargs) -> LocalEngineDefinition:
    return LocalEngineDefinition("ollama", "127.0.0.1", port, model, timeout=3.0, **kwargs)


def chat(port: int, model: str = "olala", **kwargs) -> LocalEngineDefinition:
    return LocalEngineDefinition("openai_chat", "127.0.0.1", port, model, timeout=3.0, **kwargs)


def definition(*engines: LocalEngineDefinition) -> AIRuntimeDefinition:
    return AIRuntimeDefinition(host="127.0.0.1", port=1, model=None, engines=engines)


OLLAMA_REPLY = {"response": "from ollama"}
CHAT_REPLY = {"choices": [{"message": {"content": "from olala"}}]}


def test_the_first_engine_that_answers_wins_and_the_next_is_not_asked(servers):
    first, first_calls = servers(CHAT_REPLY)
    second, second_calls = servers(OLLAMA_REPLY)

    answer = guide.ask_local(finding(), "reason", "en", "", definition(chat(first), ollama(second)))

    assert answer.reachable and answer.response == "from olala" and answer.model == "olala"
    assert first_calls == ["/v1/chat/completions"] and second_calls == []


def test_a_silent_first_engine_hands_over_and_the_answer_says_so(servers):
    second, _ = servers(OLLAMA_REPLY)

    answer = guide.ask_local(finding(), "reason", "en", "", definition(chat(dead_port(), label="olala"), ollama(second)))

    assert answer.reachable and answer.response == "from ollama"
    assert answer.model.startswith("qwen (olala: ") and "could not be reached" in answer.model


def test_when_no_engine_answers_the_reasons_come_together():
    answer = guide.ask_local(finding(), "reason", "en", "", definition(chat(dead_port(), label="olala"), ollama(dead_port())))

    assert not answer.reachable
    assert "olala: " in answer.unreachable_reason and "qwen: " in answer.unreachable_reason


def test_one_declared_engine_keeps_its_own_reason(servers):
    answer = guide.ask_local(finding(), "reason", "en", "", definition(ollama(dead_port())))

    assert not answer.reachable and "could not be reached" in answer.unreachable_reason
    assert not answer.unreachable_reason.startswith("qwen: ")


def test_without_engines_it_is_the_one_declared_ollama(servers):
    port, calls = servers(OLLAMA_REPLY)
    legacy = AIRuntimeDefinition(host="127.0.0.1", port=port, model="qwen", timeout=3.0)

    answer = guide.ask_local(finding(), "reason", "en", "", legacy)

    assert answer.response == "from ollama" and calls == ["/api/generate"]


def test_without_any_model_nothing_is_sent():
    answer = guide.ask_local(finding(), "reason", "en", "", AIRuntimeDefinition(host="127.0.0.1", port=1))

    assert not answer.reachable and answer.unreachable_reason.startswith("no model is configured")


def test_the_destination_names_the_first_declared_model(tmp_path: Path, monkeypatch):
    path = tmp_path / "ai_runtime.yml"
    path.write_text("host: h\nport: 1\nmodel: qwen\nengines:\n  - {kind: openai_chat, host: h, port: 2, model: olala-mini}\n  - {host: h, port: 1, model: qwen}\n", encoding="utf-8")
    monkeypatch.setattr(guide, "AI_RUNTIME", path)

    assert guide.ai_destination() == ("ollama", "olala-mini")


def test_a_declared_temperature_reaches_the_engine_that_is_built():
    built = guide._engine_of(chat(1, temperature=0.3))

    assert built.temperature == 0.3
    assert guide._engine_of(chat(1)).temperature is None
    assert guide._engine_of(chat(1, max_tokens=300)).max_tokens == 300
    assert guide._engine_of(chat(1)).max_tokens == 800
