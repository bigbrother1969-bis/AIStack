from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aistack.ai_runtime.openai_chat_engine import OpenAIChatEngine


class Server:
    def __init__(self) -> None:
        self.status = 200
        self.answer: object = {"choices": [{"message": {"content": "a real answer", "reasoning_content": "private thoughts"}}]}
        self.delay = 0.0
        self.bodies: list[dict[str, object]] = []
        self.paths: list[str] = []


@pytest.fixture
def server():
    state = Server()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            state.bodies.append(json.loads(self.rfile.read(length).decode("utf-8")))
            state.paths.append(self.path)
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
                pass  # a client that gave up first (the timeout test)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    state.port = httpd.server_address[1]  # type: ignore[attr-defined]
    yield state
    httpd.shutdown()
    httpd.server_close()


def engine(server, **kwargs):
    return OpenAIChatEngine("127.0.0.1", server.port, "olala-mini", timeout=kwargs.pop("timeout", 5.0), **kwargs)


def test_the_answer_is_the_content_and_never_the_reasoning_channel(server):
    text, reason = engine(server).complete("Question?")

    assert (text, reason) == ("a real answer", "")
    assert server.paths == ["/v1/chat/completions"]
    body = server.bodies[0]
    assert body["messages"] == [{"role": "user", "content": "Question?"}]
    assert body["model"] == "olala-mini" and body["stream"] is False
    assert body["temperature"] == 0.8 and body["top_p"] == 0.9 and body["top_k"] == 40
    assert "reasoning_effort" not in body


def test_a_declared_temperature_replaces_the_card_default_and_keeps_the_rest(server):
    engine(server, temperature=0.3).complete("q")
    engine(server, temperature=0.0).complete("q")

    assert server.bodies[0]["temperature"] == 0.3 and server.bodies[1]["temperature"] == 0.0
    assert server.bodies[0]["top_p"] == 0.9 and server.bodies[0]["top_k"] == 40


def test_the_reasoning_effort_is_sent_when_declared(server):
    engine(server, reasoning_effort="low").complete("q")

    assert server.bodies[0]["reasoning_effort"] == "low"


def test_a_refusal_is_reported_with_its_status(server):
    server.status = 503
    server.answer = {"error": "busy"}

    text, reason = engine(server, label="olala").complete("q")

    assert text == ""
    assert "olala refused the request with status 503" in reason


def test_an_unreachable_engine_is_reported_not_raised():
    text, reason = OpenAIChatEngine("127.0.0.1", 1, "m", timeout=2.0, label="olala").complete("q")

    assert text == "" and "olala at 127.0.0.1:1 could not be reached" in reason


def test_a_slow_answer_beyond_the_timeout_is_reported_not_raised(server):
    server.delay = 1.5

    text, reason = engine(server, timeout=0.3, label="olala").complete("q")

    assert text == "" and "did not answer within 0.3 seconds" in reason


@pytest.mark.parametrize(
    "answer",
    [{"choices": []}, {"choices": [{"message": {"content": "  "}}]}, {"choices": [{"message": {}}]}, {"choices": ["x"]}, {}],
)
def test_an_answer_with_no_text_is_reported(server, answer):
    server.answer = answer

    text, reason = engine(server, label="olala").complete("q")

    assert text == "" and "olala answered with no response text" in reason


def test_an_error_object_and_a_non_object_are_reported(server):
    server.answer = {"error": {"message": "model not loaded"}}
    assert "reported an error" in engine(server).complete("q")[1]

    server.answer = ["not", "an", "object"]
    assert "something unreadable" in engine(server).complete("q")[1]


def test_an_answer_spent_on_reasoning_says_so(server):
    server.answer = {"choices": [{"message": {"content": "", "reasoning_content": "thinking, thinking..."}}]}

    text, reason = engine(server, label="olala").complete("q")

    assert text == "" and "olala used its answer on reasoning and gave no final text" in reason
