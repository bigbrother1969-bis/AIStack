"""
`aistack.cli.linux_services_discover` (`ADR-0035`).

Driven directly against `main(environ=...)`, the same way
`test_network_docker_discover.py` drives Docker's own wiring: a
stubbed `LinuxServicesDiscoveryProvider` in place of the real one, so
no test in this file ever spawns a real `nmap`/`ssh` process or
touches a real network. What is under test is the wiring this command
itself adds: the governed definition (`network_discovery.yml` — the
same one `network_docker.discover` reads, `ADR-0035`'s second
correction, not `hosts.yml`) is loaded, the SSH key path env var name
it declares is resolved through the process environment, the provider
is built with the definition's real fields, and the resulting
observation is written as a governed artifact with Observation
History.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from aistack.cli import linux_services_discover
from aistack.tasks import linux_services_discover as task_module


OBSERVED_AT = "2026-11-28T12:00:00+00:00"

_DEFAULT_OBSERVATION: dict[str, Any] = {
    "provider": {
        "id": "aistack.provider.linux_services",
        "name": "Linux Services Discovery Provider",
    },
    "collected_at": OBSERVED_AT,
    "linux_services": {"cidr": "192.168.1.0/24", "hosts": []},
}


class FakeLinuxServicesDiscoveryProvider:
    instances: list["FakeLinuxServicesDiscoveryProvider"] = []
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
        FakeLinuxServicesDiscoveryProvider.instances.append(self)

    def collect(self) -> dict[str, Any]:
        return FakeLinuxServicesDiscoveryProvider.next_observation


@pytest.fixture(autouse=True)
def reset_fake_provider():
    FakeLinuxServicesDiscoveryProvider.instances = []
    FakeLinuxServicesDiscoveryProvider.next_observation = dict(_DEFAULT_OBSERVATION)
    yield
    FakeLinuxServicesDiscoveryProvider.instances = []
    FakeLinuxServicesDiscoveryProvider.next_observation = dict(_DEFAULT_OBSERVATION)


@pytest.fixture(autouse=True)
def no_ssh_key(monkeypatch) -> None:
    monkeypatch.delenv("AISTACK_NETWORK_SSH_KEY_PATH", raising=False)


@pytest.fixture
def stubbed_provider(monkeypatch) -> None:
    monkeypatch.setattr(
        task_module,
        "LinuxServicesDiscoveryProvider",
        FakeLinuxServicesDiscoveryProvider,
    )


@pytest.fixture
def workspace(monkeypatch, tmp_path: Path) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


# --------------------------------------------------------------------
# The real definition's fields reach the provider — the SAME definition
# `network_docker.discover` reads (`ADR-0035`'s second correction)
# --------------------------------------------------------------------


def test_the_real_definitions_cidr_and_usernames_reach_the_provider(
    stubbed_provider, workspace
):
    linux_services_discover.main()

    assert len(FakeLinuxServicesDiscoveryProvider.instances) == 1
    built = FakeLinuxServicesDiscoveryProvider.instances[0]
    assert built.cidr == "192.168.1.0/24"
    assert built.ssh_usernames == ("pi", "pi-hole")
    assert built.timeout_seconds == 3.0


def test_the_ssh_key_path_env_var_name_is_resolved_through_environ(
    stubbed_provider, workspace, monkeypatch
):
    monkeypatch.setenv("AISTACK_NETWORK_SSH_KEY_PATH", "/home/big-brother/.ssh/id_ed25519")

    linux_services_discover.main()

    built = FakeLinuxServicesDiscoveryProvider.instances[0]
    assert built.ssh_key_path == "/home/big-brother/.ssh/id_ed25519"


def test_a_missing_env_var_resolves_to_an_empty_string_not_a_raise(
    stubbed_provider, workspace
):
    linux_services_discover.main()

    built = FakeLinuxServicesDiscoveryProvider.instances[0]
    assert built.ssh_key_path == ""


# --------------------------------------------------------------------
# The observation is written as a governed artifact with History
# --------------------------------------------------------------------


def test_the_observation_is_written_with_history(stubbed_provider, workspace):
    linux_services_discover.main()

    output_path = workspace / "reports" / "generated" / "linux-services-observation.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        FakeLinuxServicesDiscoveryProvider.next_observation
    )

    history_dir = output_path.parent / "history" / "linux-services-observation"
    assert len(list(history_dir.glob("*.json"))) == 1


def test_an_identical_second_run_keeps_the_first_observation_once(
    stubbed_provider, workspace
):
    linux_services_discover.main()
    linux_services_discover.main()

    history_dir = (
        workspace
        / "reports"
        / "generated"
        / "history"
        / "linux-services-observation"
    )
    assert len(list(history_dir.glob("*.json"))) == 1


def test_a_run_with_real_discovered_hosts_writes_them_through(
    stubbed_provider, workspace
):
    FakeLinuxServicesDiscoveryProvider.next_observation = {
        "provider": {
            "id": "aistack.provider.linux_services",
            "name": "Linux Services Discovery Provider",
        },
        "collected_at": OBSERVED_AT,
        "linux_services": {
            "cidr": "192.168.1.0/24",
            "hosts": [
                {
                    "host": "192.168.1.40",
                    "ssh_username": "pi",
                    "services": [
                        {
                            "service": "mariadb",
                            "unit_state": "active",
                            "listening_ports": [3306],
                            "config_path": "/etc/mysql/mariadb.conf.d/50-server.cnf",
                            "observed_at": OBSERVED_AT,
                        }
                    ],
                }
            ],
        },
    }

    linux_services_discover.main()

    output_path = workspace / "reports" / "generated" / "linux-services-observation.json"
    written = json.loads(output_path.read_text(encoding="utf-8"))
    assert written["linux_services"]["hosts"][0]["host"] == "192.168.1.40"


# --------------------------------------------------------------------
# The Runtime executes the chain (ADR-0027 § 10)
# --------------------------------------------------------------------


def test_the_run_is_traced_and_the_trace_does_not_keep_the_key_path(
    stubbed_provider, workspace, monkeypatch
):
    monkeypatch.setenv("AISTACK_NETWORK_SSH_KEY_PATH", "/home/big-brother/.ssh/id_ed25519")

    linux_services_discover.main()

    generated = workspace / "reports" / "generated"
    traces = list((generated / "history" / "execution-trace").glob("*.json"))
    assert len(traces) == 1
    everything = "".join(
        path.read_text(encoding="utf-8") for path in generated.rglob("execution-trace*.json")
    ) + "".join(path.read_text(encoding="utf-8") for path in traces)
    assert "linux_services.discover" in everything
    assert "id_ed25519" not in everything
