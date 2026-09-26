from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest

from aistack.ai_runtime.ollama_engine import OllamaEngine


class Ollama:
    """
    A real Ollama instance, standing in — same reasoning
    `tests/unit/providers/beszel/test_beszel_provider.py`'s own
    `Hub` gives: a stub callable would test the code around the
    request, not the request itself.
    """

    def __init__(self):
        self.status = 200
        self.answer: object = {"response": "a real answer", "done": True}
        self.delay = 0.0
        self.seen: list[tuple[str, str]] = []
        self.user_agents_seen: list[str] = []


@pytest.fixture
def ollama():
    return Ollama()


@pytest.fixture
def url(ollama):
    state = ollama

    class Handler(BaseHTTPRequestHandler):

        def do_POST(self):
            parsed = urlparse(self.path)
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")

            state.seen.append((parsed.path, body))
            state.user_agents_seen.append(self.headers.get("User-Agent", ""))

            if state.delay:
                time.sleep(state.delay)

            payload = json.dumps(state.answer).encode()

            try:
                self.send_response(state.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionResetError):
                # The one test using `state.delay`
                # (`test_a_slow_answer_beyond_timeout_is_reported_not_
                # raised`) times its own client out, by design, before
                # this thread wakes from `time.sleep` — the client's
                # socket is already closed by the time a response is
                # attempted here. A real Ollama instance would meet the
                # identical thing from a real client that gave up first;
                # this is that same, ordinary case, not a defect in
                # `OllamaEngine` (which is exactly what that test's own
                # name says it proves: the timeout is reported, never
                # raised). Left unhandled, `socketserver`'s own request
                # thread printed the traceback to stderr on every run —
                # noise about this fixture's own late write, not a
                # failing assertion; `pytest` never saw it as a failure
                # either way.
                pass

        def log_message(self, *_args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    host, port = server.server_address

    try:
        yield host, port
    finally:
        server.shutdown()
        thread.join(timeout=2)


def test_a_successful_completion_returns_the_response_text(url):
    host, port = url

    engine = OllamaEngine(host=host, port=port, model="llama3.1:8b", timeout=5.0)

    text, reason = engine.complete("hello")

    assert text == "a real answer"
    assert reason == ""


def test_the_real_request_names_the_configured_model(url, ollama):
    host, port = url

    engine = OllamaEngine(host=host, port=port, model="llama3.1:8b", timeout=5.0)
    engine.complete("hello")

    path, body = ollama.seen[0]
    payload = json.loads(body)

    assert path == "/api/generate"
    assert payload["model"] == "llama3.1:8b"
    assert payload["prompt"] == "hello"
    assert payload["stream"] is False


def test_the_request_carries_an_explicit_user_agent(url, ollama):
    host, port = url

    engine = OllamaEngine(host=host, port=port, model="llama3.1:8b", timeout=5.0)
    engine.complete("hello")

    assert ollama.user_agents_seen[0] == "AIStack-AIRuntime/1.0"


def test_an_http_error_is_reported_not_raised(url, ollama):
    host, port = url
    ollama.status = 500
    ollama.answer = {"error": "model not found"}

    engine = OllamaEngine(host=host, port=port, model="unknown-model", timeout=5.0)

    text, reason = engine.complete("hello")

    assert text == ""
    assert "500" in reason


def test_an_ollama_level_error_in_a_200_is_reported(url, ollama):
    host, port = url
    ollama.answer = {"error": "model 'unknown-model' not found, try pulling it first"}

    engine = OllamaEngine(host=host, port=port, model="unknown-model", timeout=5.0)

    text, reason = engine.complete("hello")

    assert text == ""
    assert "not found" in reason


def test_an_empty_response_text_is_reported(url, ollama):
    host, port = url
    ollama.answer = {"response": "", "done": True}

    engine = OllamaEngine(host=host, port=port, model="llama3.1:8b", timeout=5.0)

    text, reason = engine.complete("hello")

    assert text == ""
    assert reason


def test_a_slow_answer_beyond_timeout_is_reported_not_raised(url, ollama):
    host, port = url
    ollama.delay = 1.0

    engine = OllamaEngine(host=host, port=port, model="llama3.1:8b", timeout=0.2)

    text, reason = engine.complete("hello")

    assert text == ""
    assert "did not answer" in reason


def test_an_unreachable_host_is_reported_not_raised():
    # Port 1 is reserved and nothing listens there — a real,
    # unreachable target rather than a mocked one, the same
    # discipline `test_beszel_provider.py` holds for its own
    # unreachable-host test.
    engine = OllamaEngine(host="127.0.0.1", port=1, model="llama3.1:8b", timeout=1.0)

    text, reason = engine.complete("hello")

    assert text == ""
    assert "could not be reached" in reason or "did not answer" in reason
