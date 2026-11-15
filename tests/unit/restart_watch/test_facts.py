from __future__ import annotations

import json
import subprocess

from aistack.restart_watch.facts import parse_inspect, parse_time, read_facts

GLUETUN = "a" * 64
QBIT = "b" * 64


def document(identifier, name, *, mode="bridge", labels=None, health=None, healthcheck=None, started="2026-11-15T08:59:12.123456789Z"):
    state = {"Running": True, "Restarting": False, "StartedAt": started}
    if health:
        state["Health"] = {"Status": health}
    return {
        "Id": identifier,
        "Name": "/" + name,
        "State": state,
        "Config": {"Labels": labels or {}, "Healthcheck": healthcheck},
        "HostConfig": {"NetworkMode": mode},
    }


def test_nanoseconds_and_the_zero_date():
    assert parse_time("2026-11-15T08:59:12.123456789Z").microsecond == 123456
    assert parse_time("0001-01-01T00:00:00Z") is None
    assert parse_time("nonsense") is None


def test_a_network_provider_is_resolved_from_its_id_to_its_name():
    facts = {
        item.name: item
        for item in parse_inspect(
            [
                document(GLUETUN, "gluetun", health="healthy", healthcheck={"Test": ["CMD", "x"]}),
                document(QBIT, "qbittorrent", mode=f"container:{GLUETUN}"),
            ]
        )
    }

    assert facts["qbittorrent"].network_provider == "gluetun"
    assert facts["gluetun"].has_healthcheck and facts["gluetun"].health == "healthy"
    assert facts["qbittorrent"].has_healthcheck is False


def test_compose_dependencies_become_container_names():
    project = {"com.docker.compose.project": "p"}
    facts = {
        item.name: item
        for item in parse_inspect(
            [
                document("1" * 64, "p-app-1", labels={**project, "com.docker.compose.service": "app",
                         "com.docker.compose.depends_on": "db:service_healthy:true,ghost:service_started:false"}),
                document("2" * 64, "p-db-1", labels={**project, "com.docker.compose.service": "db"}),
            ]
        )
    }

    assert facts["p-app-1"].depends_on == ("p-db-1",)


def test_a_disabled_healthcheck_is_not_a_healthcheck():
    facts = parse_inspect([document("1" * 64, "x", healthcheck={"Test": ["NONE"]})])

    assert facts[0].has_healthcheck is False


def test_read_facts_asks_docker_once_for_the_list_and_once_for_the_details():
    calls = []

    def run(arguments):
        calls.append(list(arguments))
        if arguments[0] == "ps":
            return subprocess.CompletedProcess(arguments, 0, f"{GLUETUN}\n", "")
        return subprocess.CompletedProcess(arguments, 0, json.dumps([document(GLUETUN, "gluetun")]), "")

    assert [f.name for f in read_facts(run)] == ["gluetun"]
    assert [c[0] for c in calls] == ["ps", "inspect"]
