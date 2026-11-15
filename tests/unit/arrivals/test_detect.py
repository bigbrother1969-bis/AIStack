from __future__ import annotations

from types import SimpleNamespace

from aistack.arrivals.definition import ArrivalsDefinition
from aistack.arrivals.detect import (
    CONTAINER,
    HOST,
    Arrival,
    observed_containers,
    update_containers,
    update_hosts,
)

NOW = "2026-11-15T12:00:00+00:00"
DEFINITION = ArrivalsDefinition()


def pass_over(state: dict, observed: dict, *, ignored=(), definition=DEFINITION):
    containers, arrivals = update_containers(state, observed, {}, definition, ignored, NOW)

    return {**state, "containers": containers, "baseline": True}, arrivals


def test_the_first_pass_only_notes_what_is_there():
    state, arrivals = pass_over({}, {"ollama": None, "koboldcpp": None})

    assert arrivals == []
    assert state["containers"]["ollama"]["announced"] is True


def test_a_container_is_said_once_on_its_second_pass_in_a_row():
    state, _ = pass_over({}, {"ollama": None})

    state, first = pass_over(state, {"ollama": None, "newone": None})
    state, second = pass_over(state, {"ollama": None, "newone": None})
    state, third = pass_over(state, {"ollama": None, "newone": None})

    assert first == []
    assert second == [Arrival(CONTAINER, "newone", None)]
    assert third == []


def test_a_container_seen_on_one_pass_only_is_never_said():
    state, _ = pass_over({}, {"ollama": None})

    state, _ = pass_over(state, {"ollama": None, "job-42": None})
    state, arrivals = pass_over(state, {"ollama": None})
    state, again = pass_over(state, {"ollama": None})

    assert arrivals == again == []
    assert "job-42" not in state["containers"]


def test_a_container_that_comes_back_is_said_again():
    state, _ = pass_over({}, {"a": None})
    state, _ = pass_over(state, {"a": None, "b": "192.168.1.11"})
    state, said = pass_over(state, {"a": None, "b": "192.168.1.11"})
    state, _ = pass_over(state, {"a": None})
    state, _ = pass_over(state, {"a": None, "b": "192.168.1.11"})
    state, back = pass_over(state, {"a": None, "b": "192.168.1.11"})

    assert said == back == [Arrival(CONTAINER, "b", "192.168.1.11")]


def test_what_is_ignored_is_never_proposed():
    state, _ = pass_over({}, {"a": None})

    state, _ = pass_over(state, {"a": None, "b": None, "c": None}, ignored=("b",), definition=ArrivalsDefinition(ignore=("c",)))
    state, arrivals = pass_over(state, {"a": None, "b": None, "c": None}, ignored=("b",), definition=ArrivalsDefinition(ignore=("c",)))

    assert arrivals == []
    assert set(state["containers"]) == {"a"}


def test_a_longer_confirmation_waits_longer():
    definition = ArrivalsDefinition(confirm_passes=3)
    state, _ = pass_over({}, {"a": None}, definition=definition)

    state, one = pass_over(state, {"a": None, "b": None}, definition=definition)
    state, two = pass_over(state, {"a": None, "b": None}, definition=definition)
    state, three = pass_over(state, {"a": None, "b": None}, definition=definition)

    assert one == two == []
    assert three == [Arrival(CONTAINER, "b", None)]


def test_the_facts_are_kept_from_one_pass_to_the_next():
    state: dict = {}
    containers, _ = update_containers(state, {"a": None}, {"a": {"image": "img:1", "ports": "80/tcp", "gpu": False}}, DEFINITION, (), NOW)
    state = {"containers": containers, "baseline": True}

    containers, _ = update_containers(state, {"a": None}, {}, DEFINITION, (), NOW)

    assert containers["a"]["image"] == "img:1"
    assert containers["a"]["gpu"] is False


def finding(subject: str, key: str, domain: str = "Écarts d'inventaire", **params: str):
    return SimpleNamespace(domain=domain, subject=subject, message=((key, tuple(params.items())),))


def test_the_undeclared_containers_are_read_from_the_inventory_findings():
    snapshot = SimpleNamespace(
        findings=(
            finding("koboldcpp", "findings.inventory_gap.undeclared_here.interpretation", container="koboldcpp"),
            finding("grafana", "findings.inventory_gap.undeclared_on_host.interpretation", container="grafana", host="192.168.1.11"),
            finding("Jellyfin", "findings.inventory_gap.missing.interpretation", service="Jellyfin", container="jellyfin"),
            finding("sda", "findings.storage.full.interpretation", domain="Stockage"),
        )
    )

    assert observed_containers(snapshot) == {"koboldcpp": None, "grafana": "192.168.1.11"}


def test_without_a_snapshot_nothing_is_read():
    assert observed_containers(None) is None


OBSERVATION = {
    "network_docker": {
        "hosts": [
            {"host": "192.168.1.11", "ssh_username": "big-brother", "containers": [{}, {}]},
            {"host": "192.168.1.57", "ssh_username": "pi", "containers": [{}]},
        ]
    }
}


def hosts(state, observation=OBSERVATION, traced=(), definition=DEFINITION, decided=()):
    waiting, known, arrivals = update_hosts(state, observation, traced, definition, decided, NOW)

    return {**state, "hosts": waiting, "known_hosts": known, "hosts_baseline": True}, arrivals


def test_the_machines_of_the_first_observation_are_not_news():
    state, arrivals = hosts({})

    assert arrivals == []
    assert state["hosts"] == {}
    assert state["known_hosts"] == ["192.168.1.11", "192.168.1.57"]


def test_a_machine_that_appears_later_is_said_once():
    state, _ = hosts({})
    newer = {"network_docker": {"hosts": [*OBSERVATION["network_docker"]["hosts"], {"host": "192.168.1.60", "ssh_username": "x", "containers": []}]}}

    state, first = hosts(state, newer)
    state, second = hosts(state, newer)

    assert first == [Arrival(HOST, "192.168.1.60", "x")]
    assert second == []
    assert state["hosts"]["192.168.1.60"]["user"] == "x"


def test_an_observation_with_no_machine_notes_nothing():
    waiting, known, arrivals = update_hosts({}, {"network_docker": {"hosts": []}}, (), DEFINITION, (), NOW)

    assert (waiting, known, arrivals) == ({}, [], [])


def test_a_traced_or_declared_or_decided_machine_is_not_news():
    state, _ = hosts({"hosts_baseline": True}, OBSERVATION, traced=("192.168.1.11",), definition=ArrivalsDefinition(known_hosts=("192.168.1.57",)))

    assert state["hosts"] == {}

    state, arrivals = hosts({"hosts_baseline": True}, OBSERVATION, decided=("192.168.1.11", "192.168.1.57"))

    assert state["hosts"] == {} and arrivals == []


def test_once_the_baseline_exists_every_machine_nobody_knows_is_news():
    state, arrivals = hosts({"hosts_baseline": True}, OBSERVATION)

    assert sorted(state["hosts"]) == ["192.168.1.11", "192.168.1.57"]
    assert len(arrivals) == 2
