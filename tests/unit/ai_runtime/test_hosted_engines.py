"""ChatGPT and Claude against a real local HTTP server: the request each sends, the answers each reads, and that the key stays in a header."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from aistack.ai_runtime.hosted_engines import AnthropicEngine, OpenAIEngine


class Server:
    def __init__(self, status: int, payload: dict[str, Any]) -> None:
        self.requests: list[dict[str, Any]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                body = self.rfile.read(int(self.headers["Content-Length"]))
                outer.requests.append({"path": self.path, "headers": {name.lower(): value for name, value in self.headers.items()}, "body": json.loads(body)})
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *args: Any) -> None:
                pass

        self.httpd = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        self.endpoint = f"http://127.0.0.1:{self.httpd.server_port}/v1/x"

    def close(self) -> None:
        self.httpd.shutdown()


def served(status: int, payload: dict[str, Any]):
    server = Server(status, payload)
    return server


@pytest.fixture
def chatgpt():
    server = served(200, {"choices": [{"message": {"role": "assistant", "content": " Bonjour GIGABYTE "}}]})
    yield server
    server.close()


@pytest.fixture
def claude():
    server = served(200, {"content": [{"type": "text", "text": "Bonjour "}, {"type": "text", "text": "GIGABYTE"}], "stop_reason": "end_turn"})
    yield server
    server.close()


def test_chatgpt_answer_is_read_and_the_key_travels_in_the_header_only(chatgpt: Server):
    engine = OpenAIEngine("gpt-x", "SECRET", 5, endpoint=chatgpt.endpoint)

    assert engine.complete("question") == ("Bonjour GIGABYTE", "")
    (request,) = chatgpt.requests
    assert request["headers"]["authorization"] == "Bearer SECRET" and "SECRET" not in request["path"]
    assert request["body"] == {"model": "gpt-x", "messages": [{"role": "user", "content": "question"}], "stream": False}
    assert "SECRET" not in repr(engine)


def test_claude_answer_is_read_and_the_key_travels_in_the_header_only(claude: Server):
    engine = AnthropicEngine("claude-x", "SECRET", 5, max_tokens=300, endpoint=claude.endpoint)

    assert engine.complete("question") == ("Bonjour GIGABYTE", "")
    (request,) = claude.requests
    assert request["headers"]["x-api-key"] == "SECRET" and "SECRET" not in request["path"]
    assert request["headers"]["anthropic-version"] == "2023-06-01"
    assert request["body"] == {"model": "claude-x", "max_tokens": 300, "messages": [{"role": "user", "content": "question"}]}
    assert "SECRET" not in repr(engine)


@pytest.mark.parametrize("make", [OpenAIEngine, AnthropicEngine])
def test_a_refusal_is_a_sentence_without_the_key(make):
    server = served(429, {"error": {"message": "Rate limit reached"}})
    try:
        text, reason = make("m", "SECRET", 5, endpoint=server.endpoint).complete("q")
    finally:
        server.close()
    assert text == "" and "429" in reason and "Rate limit" in reason and "SECRET" not in reason


@pytest.mark.parametrize("make", [OpenAIEngine, AnthropicEngine])
def test_no_key_asks_nothing(make):
    server = served(200, {})
    try:
        text, reason = make("m", "", 5, endpoint=server.endpoint).complete("q")
        assert text == "" and "no API key" in reason
        assert server.requests == []
    finally:
        server.close()


@pytest.mark.parametrize("make", [OpenAIEngine, AnthropicEngine])
def test_unreachable_is_a_sentence(make):
    text, reason = make("m", "k", 1, endpoint="http://127.0.0.1:9/x").complete("q")
    assert text == "" and "could not be reached" in reason


def test_an_answer_with_no_text_is_a_sentence():
    for engine, payload in (
        (OpenAIEngine, {"choices": [{"message": {"content": "  ", "refusal": "cannot help"}}]}),
        (AnthropicEngine, {"content": [], "stop_reason": "max_tokens"}),
    ):
        server = served(200, payload)
        try:
            text, reason = engine("m", "k", 5, endpoint=server.endpoint).complete("q")
        finally:
            server.close()
        assert text == "" and "no text" in reason
        assert ("cannot help" in reason) or ("max_tokens" in reason)


def test_an_unexpected_shape_is_a_sentence():
    server = served(200, {"unexpected": True})
    try:
        assert OpenAIEngine("m", "k", 5, endpoint=server.endpoint).complete("q")[1].endswith("gave no answer")
        assert AnthropicEngine("m", "k", 5, endpoint=server.endpoint).complete("q")[1].endswith("gave no answer")
    finally:
        server.close()
