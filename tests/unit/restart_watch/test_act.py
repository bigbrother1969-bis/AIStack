from __future__ import annotations

import json
import subprocess

from aistack.restart_watch.act import failed_probes, restart_in_order
from aistack.restart_watch.definition import Probe


class FakeDocker:
    """`docker restart` then `docker ps/inspect`, with each container's health scripted."""

    def __init__(self, healths: dict[str, list[str]], refuse: set[str] | None = None):
        self.healths = healths
        self.refuse = refuse or set()
        self.restarted: list[str] = []

    def __call__(self, arguments):
        if arguments[0] == "restart":
            if arguments[1] in self.refuse:
                return subprocess.CompletedProcess(arguments, 1, "", "no such container")
            self.restarted.append(arguments[1])
            return subprocess.CompletedProcess(arguments, 0, "", "")
        if arguments[0] == "ps":
            return subprocess.CompletedProcess(arguments, 0, "\n".join(f"id-{n}" for n in self.healths), "")
        documents = []
        for name, sequence in self.healths.items():
            health = sequence.pop(0) if len(sequence) > 1 else sequence[0]
            documents.append(
                {
                    "Id": f"id-{name}", "Name": "/" + name,
                    "State": {"Running": True, "StartedAt": "2026-11-15T09:00:00Z", "Health": {"Status": health}},
                    "Config": {"Labels": {}, "Healthcheck": {"Test": ["CMD", "x"]}},
                    "HostConfig": {"NetworkMode": "bridge"},
                }
            )
        return subprocess.CompletedProcess(arguments, 0, json.dumps(documents), "")


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def test_each_container_is_restarted_after_the_previous_one_is_healthy():
    docker, clock = FakeDocker({"gluetun": ["starting", "healthy"], "qbit": ["healthy"]}), Clock()

    outcomes = restart_in_order(["gluetun", "qbit"], {}, 60, run=docker, sleep=clock.sleep, clock=clock)

    assert [(o.name, o.ok) for o in outcomes] == [("gluetun", True), ("qbit", True)]
    assert docker.restarted == ["gluetun", "qbit"]


def test_the_plan_stops_at_the_first_container_that_does_not_come_back():
    docker, clock = FakeDocker({"gluetun": ["starting"], "qbit": ["healthy"]}), Clock()

    outcomes = restart_in_order(["gluetun", "qbit"], {}, 30, run=docker, sleep=clock.sleep, clock=clock)

    assert [(o.name, o.ok) for o in outcomes] == [("gluetun", False)]
    assert docker.restarted == ["gluetun"]
    assert "starting" in outcomes[0].detail


def test_a_refused_restart_ends_the_plan():
    docker = FakeDocker({"a": ["healthy"], "b": ["healthy"]}, refuse={"a"})

    outcomes = restart_in_order(["a", "b"], {}, 30, run=docker, sleep=lambda s: None)

    assert [(o.name, o.ok) for o in outcomes] == [("a", False)]


def test_a_dry_run_restarts_nothing():
    docker = FakeDocker({"a": ["healthy"]})

    outcomes = restart_in_order(["a"], {}, 30, run=docker, dry_run=True)

    assert docker.restarted == [] and outcomes[0].ok


def test_probes_ask_only_what_was_declared():
    probes = {"up": Probe("http://x/up"), "down": Probe("http://x/down")}

    assert failed_probes(probes, ask_probe=lambda probe: probe.url.endswith("up")) == {"down"}
