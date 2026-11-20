from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from aistack import host_engine_switch as unit

TOKEN = "a-secret-of-enough-length"


class FakeHost:
    def __init__(self, running=False, ready_after=0, docker_failure="", gpu=(7000, 1200)):
        self.is_running = running
        self.ready_after = ready_after
        self.checks = 0
        self.docker_failure = docker_failure
        self.calls: list[str] = []
        self.gpu = list(gpu)

    def running(self):
        return self.is_running

    def ready(self):
        if not self.is_running:
            return False
        self.checks += 1
        return self.checks > self.ready_after

    def docker(self, verb):
        self.calls.append(f"docker {verb}")
        if self.docker_failure:
            return self.docker_failure
        self.is_running = verb == "start"
        self.checks = 0
        return ""

    def unload_ollama(self):
        self.calls.append("unload")
        return ["qwen2.5:7b"]

    def gpu_used_mib(self):
        return self.gpu.pop(0) if self.gpu else 1200


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def switch_of(host, idle=600.0, timeout=90.0):
    clock = Clock()
    lines: list[str] = []
    return unit.Switch(host, idle, timeout, clock=clock, sleep=clock.sleep, log=lines.append), clock, lines


def test_a_start_unloads_ollama_starts_the_container_and_waits_until_it_is_ready():
    host = FakeHost(ready_after=2)
    switch, _, lines = switch_of(host)

    report = switch.start()

    assert report == {"state": "ready", "gpu_before_mib": 7000, "gpu_after_mib": 1200, "unloaded": 1}
    assert host.calls == ["unload", "docker start"]
    assert lines == ["start: ready gpu_mib 7000->1200 unloaded 1"]


def test_a_start_of_an_engine_already_ready_touches_nothing_on_the_host():
    host = FakeHost(running=True)
    switch, _, lines = switch_of(host)

    assert switch.start() == {"state": "ready"} and host.calls == [] and lines == []


def test_a_start_that_fails_says_why_and_a_start_that_never_gets_ready_gives_up():
    failing, _, _ = switch_of(FakeHost(docker_failure="docker start failed"))
    never, clock, _ = switch_of(FakeHost(ready_after=10_000), timeout=20.0)

    assert failing.start()["reason"] == "docker start failed" and failing.start()["state"] == "failed"
    gave_up = never.start()
    assert gave_up["state"] == "failed" and gave_up["reason"] == "not ready after 20 s"
    assert clock.now >= 1020.0


def test_a_stop_stops_the_container_unloads_ollama_and_forgets_the_last_use():
    host = FakeHost(running=True)
    switch, _, lines = switch_of(host)
    switch.touch()

    report = switch.stop()

    assert report["state"] == "stopped" and host.calls == ["docker stop", "unload"]
    assert switch.last_use is None and lines[0].startswith("stop: stopped gpu_mib")


def test_the_engine_is_stopped_only_after_the_idle_delay_and_a_use_renews_it():
    host = FakeHost(running=True)
    switch, clock, _ = switch_of(host, idle=600.0)
    switch.touch()

    clock.now += 599
    assert switch.stop_if_idle() is False
    switch.touch()
    clock.now += 599
    assert switch.stop_if_idle() is False
    clock.now += 2
    assert switch.stop_if_idle() is True and host.is_running is False


def test_an_engine_started_by_hand_is_stopped_too_once_the_delay_counts_from_the_first_look():
    host = FakeHost(running=True)
    switch, clock, _ = switch_of(host, idle=600.0)

    assert switch.stop_if_idle() is False and switch.last_use == clock.now
    clock.now += 601
    assert switch.stop_if_idle() is True


def test_a_stopped_engine_has_no_idle_time_and_a_touch_does_not_start_the_clock():
    host = FakeHost(running=False)
    switch, _, _ = switch_of(host)

    assert switch.touch()["state"] == "stopped" and switch.last_use is None
    assert switch.stop_if_idle() is False


@pytest.fixture
def served():
    made = []

    def start(host):
        switch, _, _ = switch_of(host)
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), unit.handler_for(switch, TOKEN))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        made.append(httpd)
        return f"http://127.0.0.1:{httpd.server_address[1]}", switch

    yield start
    for httpd in made:
        httpd.shutdown()
        httpd.server_close()


def post(url, action, token=TOKEN):
    headers = {unit.TOKEN_HEADER: token} if token is not None else {}
    request = urllib.request.Request(f"{url}/{action}", data=b"{}", headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def test_a_call_without_the_secret_or_with_another_is_refused_and_does_nothing(served):
    host = FakeHost()
    url, _ = served(host)

    assert post(url, "start", None)[0] == 403
    assert post(url, "start", "not-the-secret-at-all!!")[0] == 403
    assert host.calls == []


def test_only_the_four_actions_exist_and_nothing_comes_from_the_caller(served):
    host = FakeHost()
    url, _ = served(host)

    for path in ("restart", "exec", "start/../stop", "docker", ""):
        assert post(url, path)[0] == 404
    assert host.calls == []


def test_the_four_actions_answer_with_the_state(served):
    host = FakeHost()
    url, _ = served(host)

    assert post(url, "status") == (200, {"state": "stopped", "idle_seconds": None, "idle_limit_seconds": 600})
    assert post(url, "start")[1]["state"] == "ready"
    assert post(url, "touch")[1]["state"] == "ready"
    assert post(url, "stop")[1]["state"] == "stopped"


class _Ollama(BaseHTTPRequestHandler):
    unloaded: list[str] = []

    def do_GET(self):
        body = json.dumps({"models": [{"name": "qwen2.5:7b"}, {"name": "nomic-embed-text"}]}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        sent = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if sent.get("keep_alive") == 0:
            _Ollama.unloaded.append(sent["model"])
        self.send_response(200)
        self.send_header("Content-Length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


def test_every_model_ollama_holds_is_told_to_leave_the_gpu():
    _Ollama.unloaded = []
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Ollama)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        host = unit.Host("olala", "http://127.0.0.1:1/health", f"http://127.0.0.1:{httpd.server_address[1]}")
        assert host.unload_ollama() == ["qwen2.5:7b", "nomic-embed-text"]
    finally:
        httpd.shutdown()
        httpd.server_close()

    assert _Ollama.unloaded == ["qwen2.5:7b", "nomic-embed-text"]


def test_an_ollama_that_is_absent_or_silent_unloads_nothing_and_stops_nothing():
    assert unit.Host("olala", "http://127.0.0.1:1/health", None).unload_ollama() == []
    assert unit.Host("olala", "http://127.0.0.1:1/health", "http://127.0.0.1:1").unload_ollama() == []


def test_the_actuator_refuses_to_run_with_a_short_or_missing_secret(tmp_path, monkeypatch):
    short = tmp_path / "token"
    short.write_text("short")
    base = ["x", "--container", "olala", "--ready-url", "http://127.0.0.1:1/health"]

    monkeypatch.setattr("sys.argv", [*base, "--token-file", str(short)])
    assert unit.main() == 2
    monkeypatch.setattr("sys.argv", [*base, "--token-file", str(tmp_path / "absent")])
    assert unit.main() == 2


def test_the_gpu_figure_after_is_read_once_it_has_stopped_falling_not_at_once():
    # Ollama gave the memory back a moment after the unload: 5167 at once, then 535.
    host = FakeHost(running=True, gpu=(5167, 5167, 535, 535))
    switch, clock, _ = switch_of(host)

    report = switch.stop()

    assert report["gpu_before_mib"] == 5167 and report["gpu_after_mib"] == 535
    assert clock.now - 1000.0 <= unit.SETTLE_SECONDS


def test_nothing_is_waited_when_nothing_was_unloaded_and_the_wait_is_bounded():
    class Silent(FakeHost):
        def unload_ollama(self):
            return []

    quiet, quiet_clock, _ = switch_of(Silent(running=True, gpu=(900, 900)))
    quiet.stop()
    slow = FakeHost(running=True, gpu=tuple(range(9000, 0, -100)))
    slow_switch, slow_clock, _ = switch_of(slow)
    slow_switch.stop()

    assert quiet_clock.now == 1000.0
    assert slow_clock.now - 1000.0 <= unit.SETTLE_SECONDS
