"""`GeminiEngine` against a real local HTTP server: the request it sends, the answers it reads, and that the key never leaves the header."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest

from aistack.ai_runtime.gemini_engine import GeminiEngine


class Server:
    def __init__(self, status: int, payload: dict[str, Any]) -> None:
        self.requests: list[dict[str, Any]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                body = self.rfile.read(int(self.headers["Content-Length"]))
                outer.requests.append({"path": self.path, "key": self.headers.get("x-goog-api-key"), "body": json.loads(body)})
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
        self.endpoint = f"http://127.0.0.1:{self.httpd.server_port}/v1beta/models/{{model}}:generateContent"

    def close(self) -> None:
        self.httpd.shutdown()


@pytest.fixture
def ok():
    server = Server(200, {"candidates": [{"content": {"parts": [{"text": "Bonjour "}, {"text": "GIGABYTE"}]}}]})
    yield server
    server.close()


def test_the_answer_is_read_and_the_key_travels_in_the_header_only(ok: Server):
    engine = GeminiEngine("gemini-x", "SECRET", 5, endpoint=ok.endpoint)

    assert engine.complete("question") == ("Bonjour GIGABYTE", "")
    (request,) = ok.requests
    assert request["path"] == "/v1beta/models/gemini-x:generateContent"
    assert request["key"] == "SECRET" and "SECRET" not in request["path"]
    assert request["body"] == {"contents": [{"parts": [{"text": "question"}]}]}
    assert "SECRET" not in repr(engine)


def test_a_refusal_is_a_sentence_without_the_key():
    server = Server(429, {"error": {"message": "Resource has been exhausted"}})
    try:
        text, reason = GeminiEngine("gemini-x", "SECRET", 5, endpoint=server.endpoint).complete("q")
    finally:
        server.close()
    assert text == "" and "429" in reason and "exhausted" in reason and "SECRET" not in reason


def test_no_key_asks_nothing(ok: Server):
    assert GeminiEngine("gemini-x", "", 5, endpoint=ok.endpoint).complete("q")[0] == ""
    assert ok.requests == []


def test_unreachable_is_a_sentence():
    text, reason = GeminiEngine("m", "k", 1, endpoint="http://127.0.0.1:9/{model}").complete("q")
    assert text == "" and reason.startswith("Gemini could not be reached")
