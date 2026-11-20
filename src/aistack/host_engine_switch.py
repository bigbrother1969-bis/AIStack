#!/usr/bin/env python3
"""
aistack-engine-switch — starts an engine when a question comes, stops it when nobody asks
(`ADR-0028`, slice T4d).

One file, the Python standard library only. Installed as `/usr/local/sbin/aistack-engine-switch`, run
as root by a systemd service, reached on the loopback only.

    aistack-engine-switch --container olala --ready-url http://127.0.0.1:18095/health
        --token-file /etc/aistack/engine-switch.token [--ollama http://192.168.1.10:11434]
        [--port 18096] [--idle-minutes 10] [--start-timeout 90]

A closed list of four actions, each a `POST /<action>` that refuses a call without the secret in the
`X-Engine-Switch-Token` header: `start` (unload what Ollama holds on the GPU, start the container,
wait until it is ready), `stop`, `status`, `touch` (the engine was just used). Nothing else is
reachable: no command, no path, no container name comes from the caller. After `--idle-minutes`
without a `start` or a `touch`, the engine is stopped by the actuator itself.

With `--ollama-container`, the watcher also reads what Ollama's container logged since it started: when its
GPU discovery failed and it settled on the CPU (seen on 18 and 19 Nov. 2026) on a machine where `nvidia-smi`
answers, it restarts that one container, twice at most per run of the actuator, two minutes apart, and says so
in the journal. `--diagnose-ollama <container>` prints the verdict (`gpu`, `cpu` or `unknown`) and changes nothing.

Each transition unloads the models Ollama holds (`keep_alive: 0`) and reads the GPU memory in use
before and after, so the reader sees that it was freed. It writes one line per transition to its
standard error (the journal): the action, the state, the two figures; never a prompt or an answer.
Nothing is written to a disk; its only state is the time of the last use, in memory.
"""

from __future__ import annotations

import argparse
import hmac
import json
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOKEN_HEADER = "X-Engine-Switch-Token"
ACTIONS = ("start", "stop", "status", "touch")
CHECK_EVERY_SECONDS = 30.0
OLLAMA_MAX_RESTARTS = 2
OLLAMA_RESTART_SPACING_SECONDS = 120.0
_COMPUTE_LINE = re.compile(r'msg="?inference compute"?.*?\blibrary=(\w+)')
SETTLE_SECONDS = 10  # Ollama frees the GPU a moment after it is told to unload: read the figure once it stops falling


def compute_of_log(text: str) -> str:
    """What the log of an Ollama start says it computes on: `gpu`, `cpu`, or `unknown` when it has not said yet."""

    libraries = [found.lower() for found in _COMPUTE_LINE.findall(text)]
    if any(library != "cpu" for library in libraries):
        return "gpu"
    if libraries or "no compatible GPUs were discovered" in text:
        return "cpu"
    return "unknown"


class Host:
    """What the actuator does to the machine; replaced whole in the tests."""

    def __init__(self, container: str, ready_url: str, ollama: str | None, ollama_container: str | None = None) -> None:
        self.container = container
        self.ready_url = ready_url
        self.ollama = ollama.rstrip("/") if ollama else None
        self.ollama_container = ollama_container

    def running(self) -> bool:
        done = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", self.container],
            capture_output=True, text=True, timeout=30, check=False,
        )
        return done.returncode == 0 and done.stdout.strip() == "true"

    def ready(self) -> bool:
        try:
            with urllib.request.urlopen(self.ready_url, timeout=3) as response:
                return 200 <= response.status < 300
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def docker(self, verb: str) -> str:
        """`start` or `stop` the one container; the reason as a sentence when it fails, empty otherwise."""

        done = subprocess.run(["docker", verb, self.container], capture_output=True, text=True, timeout=120, check=False)
        return "" if done.returncode == 0 else f"docker {verb} failed"

    def unload_ollama(self) -> list[str]:
        """Models Ollama held on the GPU, now told to leave; empty when Ollama is not declared or silent."""

        if not self.ollama:
            return []
        try:
            with urllib.request.urlopen(f"{self.ollama}/api/ps", timeout=5) as response:
                loaded = [str(model.get("name")) for model in json.load(response).get("models", []) if model.get("name")]
            for name in loaded:
                request = urllib.request.Request(
                    f"{self.ollama}/api/generate",
                    data=json.dumps({"model": name, "keep_alive": 0}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(request, timeout=30).close()
            return loaded
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return []

    def ollama_compute(self) -> str:
        """`gpu`, `cpu` or `unknown`, from what Ollama's container logged since it started; `unknown` on a machine without a GPU."""

        if not self.ollama_container or self.gpu_used_mib() is None:
            return "unknown"
        seen = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}} {{.State.StartedAt}}", self.ollama_container],
            capture_output=True, text=True, timeout=30, check=False,
        )
        running, _, started = seen.stdout.strip().partition(" ")
        if seen.returncode != 0 or running != "true" or not started:
            return "unknown"
        logged = subprocess.run(
            ["docker", "logs", "--since", started, self.ollama_container],
            capture_output=True, text=True, timeout=60, check=False,
        )
        return compute_of_log(logged.stdout + "\n" + logged.stderr)

    def restart_ollama(self) -> str:
        """Restart the one Ollama container; the reason as a sentence when it fails, empty otherwise."""

        if not self.ollama_container:
            return "no container declared"
        done = subprocess.run(["docker", "restart", self.ollama_container], capture_output=True, text=True, timeout=180, check=False)
        return "" if done.returncode == 0 else "docker restart failed"

    def gpu_used_mib(self) -> int | None:
        try:
            done = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=15, check=False,
            )
            return sum(int(line) for line in done.stdout.split() if line.isdigit()) if done.returncode == 0 else None
        except (OSError, subprocess.SubprocessError):
            return None


class Switch:
    """The four actions, one at a time."""

    def __init__(
        self,
        host: Host,
        idle_seconds: float,
        start_timeout: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        log: Callable[[str], None] | None = None,
        watch_ollama: bool = False,
    ) -> None:
        self.host = host
        self.watch_ollama = watch_ollama
        self.ollama_restarts = 0
        self.last_ollama_restart: float | None = None
        self._gave_up = False
        self.idle_seconds = idle_seconds
        self.start_timeout = start_timeout
        self.clock = clock
        self.sleep = sleep
        self.log = log or (lambda line: print(line, file=sys.stderr, flush=True))
        self.last_use: float | None = None
        self._lock = threading.Lock()

    def _gpu_after(self, unloaded: int) -> int | None:
        """The GPU memory in use once what Ollama released has been given back (it falls a moment late)."""

        after = self.host.gpu_used_mib()
        if not unloaded or after is None:
            return after
        for _ in range(SETTLE_SECONDS):
            self.sleep(1.0)
            now = self.host.gpu_used_mib()
            if now is None or now >= after:
                return after
            after = now
        return after

    def status(self) -> dict[str, object]:
        running = self.host.running()
        state = "stopped" if not running else ("ready" if self.host.ready() else "starting")
        idle = None if (self.last_use is None or not running) else int(self.clock() - self.last_use)
        return {"state": state, "idle_seconds": idle, "idle_limit_seconds": int(self.idle_seconds)}

    def touch(self) -> dict[str, object]:
        with self._lock:
            if self.host.running():
                self.last_use = self.clock()
        return self.status()

    def start(self) -> dict[str, object]:
        with self._lock:
            if self.host.running() and self.host.ready():
                self.last_use = self.clock()
                return {"state": "ready"}
            before = self.host.gpu_used_mib()
            unloaded = self.host.unload_ollama()
            failure = "" if self.host.running() else self.host.docker("start")
            waited_until = self.clock() + self.start_timeout
            while not failure and not self.host.ready():
                if self.clock() >= waited_until:
                    failure = f"not ready after {int(self.start_timeout)} s"
                    break
                self.sleep(1.0)
            after = self._gpu_after(len(unloaded))
            state = "failed" if failure else "ready"
            if not failure:
                self.last_use = self.clock()
            self.log(f"start: {state} gpu_mib {before}->{after} unloaded {len(unloaded)}" + (f" ({failure})" if failure else ""))
            report: dict[str, object] = {"state": state, "gpu_before_mib": before, "gpu_after_mib": after, "unloaded": len(unloaded)}
            if failure:
                report["reason"] = failure
            return report

    def stop(self) -> dict[str, object]:
        with self._lock:
            before = self.host.gpu_used_mib()
            failure = self.host.docker("stop") if self.host.running() else ""
            unloaded = self.host.unload_ollama()
            after = self._gpu_after(len(unloaded))
            self.last_use = None
            state = "failed" if failure else "stopped"
            self.log(f"stop: {state} gpu_mib {before}->{after} unloaded {len(unloaded)}" + (f" ({failure})" if failure else ""))
            report: dict[str, object] = {"state": state, "gpu_before_mib": before, "gpu_after_mib": after, "unloaded": len(unloaded)}
            if failure:
                report["reason"] = failure
            return report

    def stop_if_idle(self) -> bool:
        """Called by the watcher: stop an engine nobody has used for the idle delay."""

        if not self.host.running():
            return False
        if self.last_use is None:
            self.last_use = self.clock()  # started by hand: the delay counts from now
            return False
        if self.clock() - self.last_use < self.idle_seconds:
            return False
        self.stop()
        return True

    def check_ollama(self) -> str:
        """Called by the watcher: restart Ollama when it started on the CPU of a machine that has a GPU. Returns the verdict read."""

        if not self.watch_ollama:
            return "unknown"
        with self._lock:
            verdict = self.host.ollama_compute()
            if verdict != "cpu":
                return verdict
            if self.ollama_restarts >= OLLAMA_MAX_RESTARTS:
                if not self._gave_up:
                    self._gave_up = True
                    self.log(f"ollama: still on the CPU after {self.ollama_restarts} restarts, none more")
                return verdict
            if self.last_ollama_restart is not None and self.clock() - self.last_ollama_restart < OLLAMA_RESTART_SPACING_SECONDS:
                return verdict
            failure = self.host.restart_ollama()
            self.ollama_restarts += 1
            self.last_ollama_restart = self.clock()
            self.log(f"ollama: started without the GPU, restart {self.ollama_restarts}/{OLLAMA_MAX_RESTARTS}" + (f" ({failure})" if failure else ""))
            return verdict

    def do(self, action: str) -> dict[str, object]:
        return {"start": self.start, "stop": self.stop, "status": self.status, "touch": self.touch}[action]()


def handler_for(switch: Switch, token: str) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            action = self.path.strip("/")
            given = self.headers.get(TOKEN_HEADER, "")
            if not hmac.compare_digest(given.encode("utf-8"), token.encode("utf-8")):
                return self._send(403, {"error": "refused"})
            if action not in ACTIONS:
                return self._send(404, {"error": "unknown action"})
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            self._send(200, switch.do(action))

        def _send(self, code: int, body: dict[str, object]) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args: object) -> None:
            pass

    return Handler


def watch(switch: Switch, stop: threading.Event, every: float = CHECK_EVERY_SECONDS) -> None:
    while not stop.wait(every):
        try:
            switch.stop_if_idle()
            switch.check_ollama()
        except (OSError, subprocess.SubprocessError) as error:
            print(f"watch failed: {type(error).__name__}", file=sys.stderr, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Start an engine on demand and stop it when nobody asks.")
    parser.add_argument("--container")
    parser.add_argument("--ready-url")
    parser.add_argument("--token-file", type=Path)
    parser.add_argument("--ollama-container", default=None, help="Ollama's container, restarted when it started on the CPU of a machine that has a GPU")
    parser.add_argument("--diagnose-ollama", metavar="CONTAINER", default=None, help="print gpu, cpu or unknown for that container and change nothing")
    parser.add_argument("--ollama", default=None, help="Ollama's address, to unload its models at each transition")
    parser.add_argument("--port", type=int, default=18096)
    parser.add_argument("--idle-minutes", type=float, default=10.0)
    parser.add_argument("--start-timeout", type=float, default=90.0)
    arguments = parser.parse_args()

    if arguments.diagnose_ollama:
        print(Host("", "", None, arguments.diagnose_ollama).ollama_compute())
        return 0
    if not (arguments.container and arguments.ready_url and arguments.token_file):
        parser.error("--container, --ready-url and --token-file are required")

    try:
        token = arguments.token_file.read_text(encoding="utf-8").strip()
    except OSError:
        print("the secret file cannot be read", file=sys.stderr)
        return 2
    if len(token) < 16:
        print("the secret is too short (16 characters at least)", file=sys.stderr)
        return 2

    host = Host(arguments.container, arguments.ready_url, arguments.ollama, arguments.ollama_container)
    switch = Switch(host, arguments.idle_minutes * 60, arguments.start_timeout, watch_ollama=bool(arguments.ollama_container))
    stop = threading.Event()
    threading.Thread(target=watch, args=(switch, stop), daemon=True).start()
    server = ThreadingHTTPServer(("127.0.0.1", arguments.port), handler_for(switch, token))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
