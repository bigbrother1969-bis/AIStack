from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from aistack.ai_runtime.definition import SwitchDefinition
from aistack.ai_runtime.engine_switch import TOKEN_HEADER, EngineSwitch, SwitchedEngine
from aistack.ai_runtime.yaml import load_ai_runtime_yaml

SECRET = "a-secret-of-enough-length"


@pytest.fixture
def actuator(tmp_path: Path):
    """A stand-in for the actuator: records the actions, answers what the test sets."""

    state = {"start": {"state": "ready"}, "calls": [], "code": 200}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if self.headers.get(TOKEN_HEADER) != SECRET:
                state["code"] = 403
            state["calls"].append(self.path.strip("/"))
            body = json.dumps(state.get(self.path.strip("/"), {"state": "ready"}) if state["code"] == 200 else {"error": "refused"}).encode()
            self.send_response(state["code"])
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    token = tmp_path / "token"
    token.write_text(SECRET + "\n")
    definition = SwitchDefinition(f"http://127.0.0.1:{httpd.server_address[1]}", str(token), 5.0)
    yield state, definition
    httpd.shutdown()
    httpd.server_close()


def test_an_engine_that_is_ready_gives_no_reason_and_a_use_is_told_to_the_switch(actuator):
    state, definition = actuator
    switch = EngineSwitch(definition, "Olala")

    assert switch.ready() == ""
    switch.used()

    assert state["calls"] == ["start", "touch"]


@pytest.mark.parametrize("answer, reason", [({"state": "failed", "reason": "not ready after 90 s"}, "not ready after 90 s"), ({"state": "starting"}, "starting")])
def test_an_engine_that_does_not_become_ready_says_why(actuator, answer, reason):
    state, definition = actuator
    state["start"] = answer

    assert EngineSwitch(definition, "Olala").ready() == f"Olala could not be started: {reason}"


def test_a_secret_that_is_wrong_or_unreadable_or_an_actuator_that_is_absent_is_a_reason_not_a_crash(actuator, tmp_path):
    state, definition = actuator
    wrong = tmp_path / "wrong"
    wrong.write_text("not-the-secret")

    refused = EngineSwitch(SwitchDefinition(definition.url, str(wrong), 5.0), "Olala").ready()
    unreadable = EngineSwitch(SwitchDefinition(definition.url, str(tmp_path / "absent"), 5.0), "Olala").ready()
    absent = EngineSwitch(SwitchDefinition("http://127.0.0.1:1", definition.token_file, 5.0), "Olala").ready()

    assert refused == "Olala could not be started: the switch refused (403)"
    assert unreadable == "Olala could not be started: the secret of the switch cannot be read"
    assert absent == "Olala could not be started: the switch cannot be reached"
    EngineSwitch(SwitchDefinition("http://127.0.0.1:1", definition.token_file, 5.0), "Olala").used()


class _Inner:
    def __init__(self):
        self.asked = 0

    def complete(self, prompt):
        self.asked += 1
        return "an answer", ""


def test_a_switched_engine_is_not_asked_unless_the_switch_says_ready_and_is_touched_after(actuator):
    state, definition = actuator
    inner = _Inner()
    engine = SwitchedEngine(inner, EngineSwitch(definition, "Olala"))

    assert engine.complete("p") == ("an answer", "") and inner.asked == 1 and state["calls"] == ["start", "touch"]

    state["start"] = {"state": "failed", "reason": "docker start failed"}
    text, reason = engine.complete("p")

    assert text == "" and reason == "Olala could not be started: docker start failed" and inner.asked == 1


def declared(tmp_path: Path, switch: str):
    path = tmp_path / "ai_runtime.yml"
    path.write_text(
        "host: h\nport: 1\nmodel: qwen\nengines:\n  - kind: openai_chat\n    host: 127.0.0.1\n    port: 18095\n"
        f"    model: olala\n{switch}",
        encoding="utf-8",
    )
    return path


def test_a_switch_loads_with_its_defaults_and_none_is_none(tmp_path):
    with_switch = load_ai_runtime_yaml(declared(tmp_path, "    switch: {url: 'http://127.0.0.1:18096/', token_file: /etc/aistack/engine-switch.token}\n"))
    without = load_ai_runtime_yaml(declared(tmp_path, ""))

    assert with_switch.engines[0].switch == SwitchDefinition("http://127.0.0.1:18096", "/etc/aistack/engine-switch.token", 90.0)
    assert without.engines[0].switch is None


@pytest.mark.parametrize(
    "switch, message",
    [
        ("{url: 'http://192.168.1.10:18096', token_file: /t}", "this host only"),
        ("{url: 'https://127.0.0.1:18096', token_file: /t}", "this host only"),
        ("{url: 'http://127.0.0.1', token_file: /t}", "this host only"),
        ("{url: 'http://127.0.0.1:18096', token_file: token}", "absolute path"),
        ("{url: 'http://127.0.0.1:18096'}", "absolute path"),
        ("{url: 'http://127.0.0.1:18096', token_file: /t, start_timeout: 1}", "from 5 to 600"),
        ("just-text", "must be a mapping"),
    ],
)
def test_a_switch_that_could_reach_beyond_the_host_or_hold_the_secret_is_refused(tmp_path, switch, message):
    with pytest.raises(ValueError, match=message):
        load_ai_runtime_yaml(declared(tmp_path, f"    switch: {switch}\n"))
