from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from aistack.arrivals import state
from aistack.arrivals.facts import local_facts, remote_facts
from aistack.arrivals.load import load_arrivals_yaml
from aistack.arrivals.propose import host_block, service_lines, suggested_description, suggested_name


def done(stdout: str, code: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess([], code, stdout, "")


def fake_docker(listing: list[dict], gpu_for: set[str] = frozenset()):  # type: ignore[assignment]
    calls: list[list[str]] = []

    def run(command: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)

        if command[:3] == ["docker", "ps", "-a"]:
            return done("\n".join(json.dumps(item) for item in listing))

        name = command[-1]
        return done('[{"Driver":"nvidia","Capabilities":[["gpu"]]}]' if name in gpu_for else "null")

    run.calls = calls  # type: ignore[attr-defined]
    return run


def test_local_facts_give_image_ports_and_gpu_of_the_asked_containers_only():
    run = fake_docker(
        [
            {"Names": "koboldcpp", "Image": "koboldcpp:local", "Ports": "192.168.1.10:5001->5001/tcp"},
            {"Names": "ollama", "Image": "ollama/ollama", "Ports": ""},
        ],
        gpu_for={"koboldcpp"},
    )

    assert local_facts({"koboldcpp"}, run) == {
        "koboldcpp": {"image": "koboldcpp:local", "ports": "192.168.1.10:5001->5001/tcp", "gpu": True}
    }
    assert not any(call[:2] == ["docker", "inspect"] and call[-1] == "ollama" for call in run.calls)


def test_no_container_asked_means_no_docker_call():
    run = fake_docker([])

    assert local_facts(set(), run) == {}
    assert run.calls == []


def test_when_docker_does_not_answer_nothing_is_guessed():
    def broken(command: list[str], **_: object):
        raise OSError("no docker")

    assert local_facts({"a"}, broken) == {}
    assert local_facts({"a"}, lambda command, **_: done("", 1)) == {}


def test_remote_facts_come_from_the_discovery_of_the_right_machine():
    observation = {
        "network_docker": {
            "hosts": [
                {"host": "192.168.1.11", "containers": [{"Names": "grafana", "Image": "grafana/grafana", "Ports": "3000/tcp"}]},
                {"host": "192.168.1.40", "containers": [{"Names": "grafana", "Image": "other"}]},
            ]
        }
    }

    assert remote_facts(observation, {"grafana": "192.168.1.11"}) == {"grafana": {"image": "grafana/grafana", "ports": "3000/tcp"}}


def test_the_shipped_declaration_is_neutral():
    from aistack.arrivals import load as module

    shipped = Path(module.__file__).parent / "definitions" / "arrivals.yml"
    definition = load_arrivals_yaml(shipped)

    assert definition.confirm_passes == 2
    assert definition.machine_scan_hours == 0
    assert definition.ignore == () and definition.known_hosts == ()


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("confirm_passes: 0\n", "confirm_passes"),
        ("confirm_passes: yes\n", "confirm_passes"),
        ("machine_scan_hours: -1\n", "machine_scan_hours"),
        ("ignore: a\n", "ignore"),
        ("known_hosts: [1]\n", "known_hosts"),
        ("- a\n", "mapping"),
    ],
)
def test_a_wrong_declaration_names_the_file_and_the_key(tmp_path: Path, text: str, message: str):
    path = tmp_path / "arrivals.yml"
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_arrivals_yaml(path)


def test_an_empty_declaration_is_the_defaults(tmp_path: Path):
    path = tmp_path / "arrivals.yml"
    path.write_text("", encoding="utf-8")

    assert load_arrivals_yaml(path).confirm_passes == 2


def test_state_and_decisions_survive_a_round_trip_and_a_missing_file_is_empty(tmp_path: Path):
    assert state.read_state(tmp_path) == {}
    assert state.read_decisions(tmp_path) == {"ignored_containers": [], "known_hosts": []}
    assert state.read_observation(tmp_path) == {}

    state.write_state(tmp_path, {"baseline": True})
    state.write_decisions(tmp_path, {"ignored_containers": ["b", "a", "a"], "known_hosts": ["192.168.1.9"]})

    assert state.read_state(tmp_path) == {"baseline": True}
    assert state.read_decisions(tmp_path) == {"ignored_containers": ["a", "b"], "known_hosts": ["192.168.1.9"]}


def test_a_damaged_state_file_is_an_empty_state(tmp_path: Path):
    (tmp_path / state.STATE_FILE).write_text("{not json", encoding="utf-8")

    assert state.read_state(tmp_path) == {}


def test_proposals():
    assert suggested_name("stable-diffusion_ui") == "Stable Diffusion Ui"
    assert suggested_description("img:1", "80/tcp", True) == "img:1 — 80/tcp — GPU"
    assert suggested_description(None, None, False) == ""
    assert service_lines("  ", 'A "b"', "c", "") == ['  - name: "A \\"b\\""', '    container: "c"']
    assert host_block("192.168.1.57", "pi") == (
        "# ssh pi@192.168.1.57\nhosts:\n  machine-57:\n    directory: hosts/machine-57\n    address: 192.168.1.57\n"
    )
