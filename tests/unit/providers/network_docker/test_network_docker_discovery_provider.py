"""
`NetworkDockerDiscoveryProvider` — `claude/PLAN-J11-CONSOLE-2026-09-11.md`
§11.

Neither `nmap` nor `ssh` is ever really invoked here: `run_command`
is injected with a fake standing in for `subprocess.run`, the same
boundary `ComposeProvider`'s own tests stub `DockerProvider` at —
what is under test is this provider's own parsing and per-host
decision logic, not a real network or a real remote daemon.
"""

from __future__ import annotations

import subprocess
from typing import Any

from aistack.providers.network_docker import NetworkDockerDiscoveryProvider

NMAP_TWO_HOSTS_UP = """\
# Nmap 7.95 scan initiated
Host: 192.168.1.10 ()\tStatus: Up
Host: 192.168.1.40 ()\tStatus: Up
Host: 192.168.1.99 ()\tStatus: Up
Host: 192.168.1.150 ()\tStatus: Down
# Nmap done
"""


def completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class FakeRunner:
    """
    Routes on the command's own shape — `nmap ...` vs `ssh ... user@ip ...`
    — and answers per `(ip, username)` from a declared table. A
    combination not declared reads as a failed connection, exactly
    like a real host that refuses that username.
    """

    def __init__(
        self,
        nmap_stdout: str = "",
        nmap_returncode: int = 0,
        ssh_table: dict[tuple[str, str], tuple[int, str]] | None = None,
        raise_on_nmap: bool = False,
    ) -> None:
        self.nmap_stdout = nmap_stdout
        self.nmap_returncode = nmap_returncode
        self.ssh_table = ssh_table or {}
        self.raise_on_nmap = raise_on_nmap
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append(command)

        if command[0] == "nmap":
            if self.raise_on_nmap:
                raise OSError("nmap not found")
            return completed(self.nmap_returncode, self.nmap_stdout)

        if command[0] == "ssh":
            target = command[-2]
            username, _, ip = target.partition("@")
            returncode, stdout = self.ssh_table.get((ip, username), (255, ""))
            return completed(returncode, stdout)

        raise AssertionError(f"unexpected command: {command}")


def provider(runner: FakeRunner, usernames: tuple[str, ...] = ("pi", "pi-hole")):
    return NetworkDockerDiscoveryProvider(
        cidr="192.168.1.0/24",
        ssh_key_path="/home/big-brother/.ssh/id_ed25519",
        ssh_usernames=usernames,
        run_command=runner,
        local_ips=frozenset({"192.168.1.10"}),
    )


# --------------------------------------------------------------------
# The real, common case
# --------------------------------------------------------------------


def test_a_live_host_that_authenticates_is_observed():
    runner = FakeRunner(
        nmap_stdout=NMAP_TWO_HOSTS_UP,
        ssh_table={
            ("192.168.1.40", "pi"): (
                0,
                '{"Names":"beszel-agent","Image":"henrygd/beszel-agent"}\n',
            ),
        },
    )

    observation = provider(runner).collect()
    hosts = observation["network_docker"]["hosts"]

    assert len(hosts) == 1
    assert hosts[0]["host"] == "192.168.1.40"
    assert hosts[0]["ssh_username"] == "pi"
    assert hosts[0]["containers"] == [
        {"Names": "beszel-agent", "Image": "henrygd/beszel-agent"}
    ]


def test_several_hosts_are_all_observed():
    runner = FakeRunner(
        nmap_stdout=NMAP_TWO_HOSTS_UP,
        ssh_table={
            ("192.168.1.40", "pi"): (0, '{"Names":"a"}\n'),
            ("192.168.1.99", "pi-hole"): (0, '{"Names":"b"}\n'),
        },
    )

    observation = provider(runner).collect()
    hosts = observation["network_docker"]["hosts"]

    assert [host["host"] for host in hosts] == ["192.168.1.40", "192.168.1.99"]


# --------------------------------------------------------------------
# Usernames are tried in order, first success wins
# --------------------------------------------------------------------


def test_a_later_username_is_tried_when_the_first_fails():
    runner = FakeRunner(
        nmap_stdout=NMAP_TWO_HOSTS_UP,
        ssh_table={
            ("192.168.1.99", "pi-hole"): (0, '{"Names":"scrutiny-collector"}\n'),
        },
    )

    observation = provider(runner).collect()
    hosts = observation["network_docker"]["hosts"]

    assert len(hosts) == 1
    assert hosts[0]["ssh_username"] == "pi-hole"


def test_the_first_username_that_authenticates_wins_not_a_later_one():
    runner = FakeRunner(
        nmap_stdout="Host: 192.168.1.40 ()\tStatus: Up\n",
        ssh_table={
            ("192.168.1.40", "pi"): (0, '{"Names":"a"}\n'),
            ("192.168.1.40", "pi-hole"): (0, '{"Names":"should-not-be-used"}\n'),
        },
    )

    observation = provider(runner).collect()
    hosts = observation["network_docker"]["hosts"]

    assert hosts[0]["ssh_username"] == "pi"
    assert hosts[0]["containers"] == [{"Names": "a"}]


# --------------------------------------------------------------------
# "Nothing observed, nothing rendered" — no relationship asserted
# --------------------------------------------------------------------


def test_a_host_that_matches_no_username_is_absent():
    runner = FakeRunner(nmap_stdout="Host: 192.168.1.40 ()\tStatus: Up\n", ssh_table={})

    observation = provider(runner).collect()
    assert observation["network_docker"]["hosts"] == []


def test_nmap_raising_yields_no_hosts_and_no_ssh_attempts():
    runner = FakeRunner(raise_on_nmap=True)

    observation = provider(runner).collect()

    assert observation["network_docker"]["hosts"] == []
    assert all(call[0] != "ssh" for call in runner.calls)


def test_nmap_non_zero_exit_yields_no_hosts():
    runner = FakeRunner(nmap_stdout=NMAP_TWO_HOSTS_UP, nmap_returncode=1)

    observation = provider(runner).collect()
    assert observation["network_docker"]["hosts"] == []


def test_a_down_host_in_nmap_output_is_never_tried():
    runner = FakeRunner(
        nmap_stdout="Host: 192.168.1.150 ()\tStatus: Down\n",
        ssh_table={("192.168.1.150", "pi"): (0, '{"Names":"a"}\n')},
    )

    observation = provider(runner).collect()

    assert observation["network_docker"]["hosts"] == []
    assert all(call[0] != "ssh" for call in runner.calls)


def test_ssh_raising_oserror_is_treated_as_a_failed_attempt(monkeypatch):
    class RaisingRunner(FakeRunner):
        def __call__(self, command, **kwargs):
            if command[0] == "ssh":
                raise OSError("ssh not found")
            return super().__call__(command, **kwargs)

    runner = RaisingRunner(nmap_stdout="Host: 192.168.1.40 ()\tStatus: Up\n")

    observation = provider(runner).collect()
    assert observation["network_docker"]["hosts"] == []


def test_malformed_json_lines_are_skipped_not_raised():
    runner = FakeRunner(
        nmap_stdout="Host: 192.168.1.40 ()\tStatus: Up\n",
        ssh_table={
            ("192.168.1.40", "pi"): (
                0,
                '{"Names":"a"}\nnot json\n{"Names":"b"}\n',
            ),
        },
    )

    observation = provider(runner).collect()
    hosts = observation["network_docker"]["hosts"]

    assert hosts[0]["containers"] == [{"Names": "a"}, {"Names": "b"}]


def test_a_host_with_no_containers_is_still_observed_with_an_empty_list():
    runner = FakeRunner(
        nmap_stdout="Host: 192.168.1.40 ()\tStatus: Up\n",
        ssh_table={("192.168.1.40", "pi"): (0, "")},
    )

    observation = provider(runner).collect()
    hosts = observation["network_docker"]["hosts"]

    assert hosts[0]["containers"] == []


# --------------------------------------------------------------------
# The local machine is never SSH'd into as if it were remote
# --------------------------------------------------------------------


def test_the_local_machines_own_ip_is_never_tried_over_ssh():
    runner = FakeRunner(
        nmap_stdout=NMAP_TWO_HOSTS_UP,
        ssh_table={("192.168.1.10", "pi"): (0, '{"Names":"should-not-appear"}\n')},
    )

    observation = provider(runner).collect()
    hosts = observation["network_docker"]["hosts"]

    assert all(host["host"] != "192.168.1.10" for host in hosts)
    assert not any(
        call[0] == "ssh" and call[-2].endswith("@192.168.1.10") for call in runner.calls
    )


def test_local_ip_detection_returns_at_least_loopback_when_not_overridden():
    """
    A real socket call (a UDP "connect", which never actually sends a
    packet) — no network access required, so this stays deterministic
    and safe to run in a sandboxed test environment.
    """

    discovery = NetworkDockerDiscoveryProvider(
        cidr="192.168.1.0/24",
        ssh_key_path="/dev/null",
        ssh_usernames=(),
        run_command=FakeRunner(),
    )

    local_ips = discovery._detect_local_ips()
    assert "127.0.0.1" in local_ips


# --------------------------------------------------------------------
# Shape and determinism
# --------------------------------------------------------------------


def test_the_observation_carries_provider_identity_and_cidr():
    runner = FakeRunner()
    observation = provider(runner).collect()

    assert observation["provider"]["id"] == "aistack.provider.network_docker"
    assert observation["network_docker"]["cidr"] == "192.168.1.0/24"
    assert "collected_at" in observation


def test_hosts_are_sorted_regardless_of_discovery_order():
    runner = FakeRunner(
        nmap_stdout=(
            "Host: 192.168.1.99 ()\tStatus: Up\n"
            "Host: 192.168.1.40 ()\tStatus: Up\n"
        ),
        ssh_table={
            ("192.168.1.40", "pi"): (0, '{"Names":"a"}\n'),
            ("192.168.1.99", "pi-hole"): (0, '{"Names":"b"}\n'),
        },
    )

    observation = provider(runner).collect()
    hosts = observation["network_docker"]["hosts"]

    assert [host["host"] for host in hosts] == ["192.168.1.40", "192.168.1.99"]


def test_the_declared_ssh_key_path_is_passed_to_ssh():
    runner = FakeRunner(
        nmap_stdout="Host: 192.168.1.40 ()\tStatus: Up\n",
        ssh_table={("192.168.1.40", "pi"): (0, "")},
    )

    provider(runner).collect()

    ssh_calls = [call for call in runner.calls if call[0] == "ssh"]
    assert ssh_calls
    assert "/home/big-brother/.ssh/id_ed25519" in ssh_calls[0]


def test_the_remote_docker_ps_format_is_shell_quoted():
    """
    Real-world defect found 2026-09-12, on the owner's real Raspberry
    Pi: `--format {{json .}}` sent unquoted is still one Python
    string, but ssh hands it to the *remote* shell as free text — the
    space inside `{{json .}}` splits it into two words there, `docker
    ps` receives an unexpected extra argument and fails ("docker ps
    accepts no arguments", exit code 1), and this provider's own
    tolerant design silently reads that failure as "no Docker on this
    host". None of this file's `FakeRunner`-based tests caught it,
    because `FakeRunner` routes on `(ip, username)` and never
    inspects the remote command string itself — this test does.
    """

    runner = FakeRunner(
        nmap_stdout="Host: 192.168.1.40 ()\tStatus: Up\n",
        ssh_table={("192.168.1.40", "pi"): (0, "")},
    )

    provider(runner).collect()

    ssh_calls = [call for call in runner.calls if call[0] == "ssh"]
    assert ssh_calls
    assert ssh_calls[0][-1] == "docker ps -a --format '{{json .}}'"
