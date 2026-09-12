"""
`aistack.cli.network_docker_discover` — `claude/PLAN-J11-CONSOLE-2026-09-11.md`
§11.

Driven directly against `main(environ=...)`, the same way
`test_architecture_render_beszel.py` drives Beszel's own wiring: a
stubbed `NetworkDockerDiscoveryProvider` in place of the real one, so
no test in this file ever spawns a real `nmap`/`ssh` process or
touches a real network. What is under test is the wiring this
command itself adds: the governed definition is loaded, the SSH key
path env var name it declares is resolved through the given
`environ` (never the path itself hardcoded here), the provider is
built with the definition's real fields, and the resulting
observation is written as a governed artifact with Observation
History.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aistack.cli import network_docker_discover


OBSERVED_AT = "2026-09-12T12:00:00+00:00"

_DEFAULT_OBSERVATION: dict[str, Any] = {
    "provider": {
        "id": "aistack.provider.network_docker",
        "name": "Network Docker Discovery Provider",
    },
    "collected_at": OBSERVED_AT,
    "network_docker": {"cidr": "192.168.1.0/24", "hosts": []},
}


class FakeNetworkDockerDiscoveryProvider:
    instances: list["FakeNetworkDockerDiscoveryProvider"] = []
    next_observation: dict[str, Any]

    def __init__(
        self,
        cidr: str,
        ssh_key_path: str,
        ssh_usernames: tuple[str, ...],
        timeout_seconds: float = 3.0,
    ) -> None:
        self.cidr = cidr
        self.ssh_key_path = ssh_key_path
        self.ssh_usernames = ssh_usernames
        self.timeout_seconds = timeout_seconds
        FakeNetworkDockerDiscoveryProvider.instances.append(self)

    def collect(self) -> dict[str, Any]:
        return FakeNetworkDockerDiscoveryProvider.next_observation


@pytest.fixture(autouse=True)
def reset_fake_provider():
    FakeNetworkDockerDiscoveryProvider.instances = []
    FakeNetworkDockerDiscoveryProvider.next_observation = dict(_DEFAULT_OBSERVATION)
    yield
    FakeNetworkDockerDiscoveryProvider.instances = []
    FakeNetworkDockerDiscoveryProvider.next_observation = dict(_DEFAULT_OBSERVATION)


@pytest.fixture
def stubbed_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        network_docker_discover,
        "NetworkDockerDiscoveryProvider",
        FakeNetworkDockerDiscoveryProvider,
    )


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------------------
# The real definition's fields reach the provider
# --------------------------------------------------------------------


def test_the_real_definitions_cidr_and_usernames_reach_the_provider(
    stubbed_provider, workspace
):
    network_docker_discover.main(environ={})

    assert len(FakeNetworkDockerDiscoveryProvider.instances) == 1
    built = FakeNetworkDockerDiscoveryProvider.instances[0]
    assert built.cidr == "192.168.1.0/24"
    assert built.ssh_usernames == ("pi", "pi-hole")
    assert built.timeout_seconds == 3.0


# --------------------------------------------------------------------
# The env var NAME is declared, the VALUE is resolved through environ
# --------------------------------------------------------------------


def test_the_ssh_key_path_env_var_name_is_resolved_through_environ(
    stubbed_provider, workspace
):
    network_docker_discover.main(
        environ={"AISTACK_NETWORK_SSH_KEY_PATH": "/home/big-brother/.ssh/id_ed25519"}
    )

    built = FakeNetworkDockerDiscoveryProvider.instances[0]
    assert built.ssh_key_path == "/home/big-brother/.ssh/id_ed25519"


def test_a_missing_env_var_resolves_to_an_empty_string_not_a_raise(
    stubbed_provider, workspace
):
    network_docker_discover.main(environ={})

    built = FakeNetworkDockerDiscoveryProvider.instances[0]
    assert built.ssh_key_path == ""


# --------------------------------------------------------------------
# The observation is written as a governed artifact with History
# --------------------------------------------------------------------


def test_the_observation_is_written_with_history(stubbed_provider, workspace):
    network_docker_discover.main(environ={})

    output_path = workspace / "reports" / "generated" / "network-docker-observation.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        FakeNetworkDockerDiscoveryProvider.next_observation
    )

    history_dir = output_path.parent / "history" / "network-docker-observation"
    assert len(list(history_dir.glob("*.json"))) == 1


def test_a_second_run_does_not_erase_the_first_observation(
    stubbed_provider, workspace
):
    network_docker_discover.main(environ={})
    network_docker_discover.main(environ={})

    history_dir = (
        workspace
        / "reports"
        / "generated"
        / "history"
        / "network-docker-observation"
    )
    assert len(list(history_dir.glob("*.json"))) == 2


def test_a_run_with_real_discovered_hosts_writes_them_through(
    stubbed_provider, workspace
):
    FakeNetworkDockerDiscoveryProvider.next_observation = {
        "provider": {
            "id": "aistack.provider.network_docker",
            "name": "Network Docker Discovery Provider",
        },
        "collected_at": OBSERVED_AT,
        "network_docker": {
            "cidr": "192.168.1.0/24",
            "hosts": [
                {
                    "host": "192.168.1.40",
                    "ssh_username": "pi",
                    "containers": [{"Names": "beszel-agent"}],
                }
            ],
        },
    }

    network_docker_discover.main(environ={})

    output_path = workspace / "reports" / "generated" / "network-docker-observation.json"
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["network_docker"]["hosts"][0]["host"] == "192.168.1.40"
