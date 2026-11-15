from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from aistack.arrivals import state
from aistack.arrivals.definition import ArrivalsDefinition
from aistack.arrivals.detect import CONTAINER, HOST, Arrival
from aistack.arrivals.run import due, remember
from aistack.arrivals.run import run as one_pass

T0 = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
KEY = "findings.inventory_gap.undeclared_here.interpretation"


def snapshot(*names: str):
    return SimpleNamespace(
        findings=tuple(SimpleNamespace(domain="Écarts d'inventaire", subject=n, message=((KEY, (("container", n),)),)) for n in names)
    )


def facts(names):
    return {n: {"image": f"{n}:1", "ports": "80/tcp", "gpu": False} for n in names}


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


def run(generated: Path, *args, dry_run: bool = False, **kwargs):
    """A pass as the vigil makes it: the state is kept once the message went."""

    arrivals, following = one_pass(generated, *args, **kwargs)

    if not dry_run:
        remember(generated, following)

    return arrivals


def test_a_new_container_is_said_on_the_second_pass_and_its_facts_are_kept(tmp_path: Path):
    definition = ArrivalsDefinition()

    assert run(tmp_path, definition, snapshot("ollama"), (), now=at(0), facts=facts) == []
    assert run(tmp_path, definition, snapshot("ollama", "koboldcpp"), (), now=at(15), facts=facts) == []
    said = run(tmp_path, definition, snapshot("ollama", "koboldcpp"), (), now=at(30), facts=facts)

    assert said == [Arrival(CONTAINER, "koboldcpp", None)]
    assert state.read_state(tmp_path)["containers"]["koboldcpp"]["image"] == "koboldcpp:1"


def test_facts_are_asked_only_for_the_containers_that_have_none(tmp_path: Path):
    asked: list[list[str]] = []

    def spy(names):
        asked.append(sorted(names))
        return facts(names)

    definition = ArrivalsDefinition()
    run(tmp_path, definition, snapshot("a"), (), now=at(0), facts=spy)
    run(tmp_path, definition, snapshot("a", "b"), (), now=at(15), facts=spy)
    run(tmp_path, definition, snapshot("a", "b"), (), now=at(30), facts=spy)

    assert asked == [["a"], ["b"], []]


def test_without_a_snapshot_the_containers_are_left_as_they_were(tmp_path: Path):
    definition = ArrivalsDefinition()
    run(tmp_path, definition, snapshot("a"), (), now=at(0), facts=facts)
    run(tmp_path, definition, snapshot("a", "b"), (), now=at(15), facts=facts)

    assert run(tmp_path, definition, None, (), now=at(30), facts=facts) == []
    assert set(state.read_state(tmp_path)["containers"]) == {"a", "b"}


def test_a_dry_run_says_but_writes_nothing(tmp_path: Path):
    run(tmp_path, ArrivalsDefinition(), snapshot("a"), (), now=at(0), facts=facts, dry_run=True)

    assert state.read_state(tmp_path) == {}


def observation(*addresses: str) -> dict:
    return {"network_docker": {"hosts": [{"host": a, "ssh_username": "u", "containers": []} for a in addresses]}}


def test_the_scan_runs_only_when_due_and_its_machines_are_news_after_the_first_one(tmp_path: Path):
    definition = ArrivalsDefinition(machine_scan_hours=24)
    scans = []
    (tmp_path / state.OBSERVATION_FILE).write_text(json.dumps(observation("192.168.1.11")), encoding="utf-8")

    def scan():
        scans.append(1)

    assert run(tmp_path, definition, None, (), now=at(0), scan=scan) == []
    assert run(tmp_path, definition, None, (), now=at(60), scan=scan) == []
    assert len(scans) == 1

    (tmp_path / state.OBSERVATION_FILE).write_text(json.dumps(observation("192.168.1.11", "192.168.1.60")), encoding="utf-8")
    said = run(tmp_path, definition, None, (), now=at(24 * 60 + 1), scan=scan)

    assert said == [Arrival(HOST, "192.168.1.60", "u")]
    assert len(scans) == 2


def test_a_scan_that_found_nothing_does_not_make_the_next_machines_old_news(tmp_path: Path):
    definition = ArrivalsDefinition(machine_scan_hours=24)
    (tmp_path / state.OBSERVATION_FILE).write_text(json.dumps(observation()), encoding="utf-8")

    run(tmp_path, definition, None, (), now=at(0), scan=lambda: None)
    (tmp_path / state.OBSERVATION_FILE).write_text(json.dumps(observation("192.168.1.11")), encoding="utf-8")
    run(tmp_path, definition, None, (), now=at(5), scan=None)

    assert state.read_state(tmp_path)["hosts"] == {}
    assert state.read_state(tmp_path)["known_hosts"] == ["192.168.1.11"]


def test_with_no_scan_asked_the_observation_the_owner_made_is_still_read(tmp_path: Path):
    (tmp_path / state.OBSERVATION_FILE).write_text(json.dumps(observation("192.168.1.11")), encoding="utf-8")

    run(tmp_path, ArrivalsDefinition(), None, (), now=at(0), scan=lambda: (_ for _ in ()).throw(AssertionError("scanned")))

    assert state.read_state(tmp_path)["known_hosts"] == ["192.168.1.11"]


def test_due():
    assert due(None, T0, 24) and due("junk", T0, 24)
    assert not due(None, T0, 0)
    assert not due(T0.isoformat(), T0 + timedelta(hours=23), 24)
    assert due(T0.isoformat(), T0 + timedelta(hours=24), 24)
