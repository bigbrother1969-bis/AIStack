"""
`LinuxServicesDiscoveryProvider` (`ADR-0035`).

Neither `nmap` nor `ssh` is ever really invoked here: `run_command` is
injected with a fake standing in for `subprocess.run`, the same
boundary `NetworkDockerDiscoveryProvider`'s own tests stub at — this
provider reuses that one's CIDR sweep and SSH-credential mechanism
verbatim (`network_discovery.yml`, not `hosts.yml` — `ADR-0035`'s
second correction), so its discovery-and-authentication tests are not
repeated here; what is under test is this provider's own per-service
collection and tolerance for a partially-reachable host.
"""

from __future__ import annotations

import subprocess
from typing import Any

from aistack.providers.linux_services import LinuxServicesDiscoveryProvider

NMAP_ONE_HOST_UP = "Host: 192.168.1.40 ()\tStatus: Up\n"
NMAP_TWO_HOSTS_UP = (
    "Host: 192.168.1.40 ()\tStatus: Up\n"
    "Host: 192.168.1.99 ()\tStatus: Up\n"
)

_UNIT_FOR = {
    "mariadb": "mariadb.service",
    "postgresql": "postgresql.service",
    "apache": "apache2.service",
    "php": "php-fpm.service",
}


def completed(returncode: int = 0, stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr="")


class FakeRunner:
    """
    Routes on the command's own shape — `nmap ...` vs
    `ssh ... user@ip <remote command>` — and answers SSH calls from a
    declared table keyed by `(ip, username, remote_command)`. A
    combination not declared reads as a failed command, exactly like a
    real host that refuses it or doesn't have it.
    """

    def __init__(
        self,
        nmap_stdout: str = "",
        nmap_returncode: int = 0,
        ssh_table: dict[tuple[str, str, str], tuple[int, str]] | None = None,
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
            remote_command = command[-1]
            username, _, ip = target.partition("@")
            returncode, stdout = self.ssh_table.get((ip, username, remote_command), (255, ""))
            return completed(returncode, stdout)

        raise AssertionError(f"unexpected command: {command}")


def provider(runner: FakeRunner, usernames: tuple[str, ...] = ("pi", "pi-hole")):
    return LinuxServicesDiscoveryProvider(
        cidr="192.168.1.0/24",
        ssh_key_path="/home/big-brother/.ssh/id_ed25519",
        ssh_usernames=usernames,
        run_command=runner,
        local_ips=frozenset({"192.168.1.10"}),
    )


def full_table(ip: str, username: str, *, ss_output: str = "") -> dict[tuple[str, str, str], tuple[int, str]]:
    """Every target service active, with a package version, listening
    on its expected port, and its config file present."""

    table: dict[tuple[str, str, str], tuple[int, str]] = {
        (ip, username, "ss -tlnp"): (0, ss_output),
    }

    for unit in _UNIT_FOR.values():
        table[(ip, username, f"systemctl is-active {unit}")] = (0, "active\n")

    return table


# --------------------------------------------------------------------
# The real, common case
# --------------------------------------------------------------------


def test_a_live_host_that_authenticates_is_observed_on_all_four_services():
    ip, username = "192.168.1.40", "pi"
    table = full_table(ip, username, ss_output="LISTEN 0 151 *:3306 *:*\n")
    table[(ip, username, "dpkg-query -W -f='${Version}' mariadb-server 2>/dev/null")] = (
        0,
        "1:10.11.6-0+deb12u1\n",
    )
    table[(ip, username, "test -e /etc/mysql/mariadb.conf.d/50-server.cnf && echo present")] = (
        0,
        "present\n",
    )

    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, ssh_table=table)

    observation = provider(runner).collect()
    hosts = observation["linux_services"]["hosts"]

    assert len(hosts) == 1
    assert hosts[0]["host"] == ip
    assert hosts[0]["ssh_username"] == username

    services = {entry["service"]: entry for entry in hosts[0]["services"]}
    assert set(services) == {"mariadb", "postgresql", "apache", "php"}

    mariadb = services["mariadb"]
    assert mariadb["unit_state"] == "active"
    assert mariadb["package_version"] == "1:10.11.6-0+deb12u1"
    assert mariadb["listening_ports"] == [3306]
    assert mariadb["config_path"] == "/etc/mysql/mariadb.conf.d/50-server.cnf"
    assert "observed_at" in mariadb


def test_several_hosts_are_all_observed_and_sorted():
    runner = FakeRunner(
        nmap_stdout=NMAP_TWO_HOSTS_UP,
        ssh_table={
            **full_table("192.168.1.99", "pi-hole"),
            **full_table("192.168.1.40", "pi"),
        },
    )

    observation = provider(runner).collect()
    hosts = observation["linux_services"]["hosts"]

    assert [host["host"] for host in hosts] == ["192.168.1.40", "192.168.1.99"]


# --------------------------------------------------------------------
# Usernames are tried in order, first success wins
# --------------------------------------------------------------------


def test_a_later_username_is_tried_when_the_first_fails():
    runner = FakeRunner(
        nmap_stdout=NMAP_ONE_HOST_UP,
        ssh_table=full_table("192.168.1.40", "pi-hole"),
    )

    observation = provider(runner).collect()
    hosts = observation["linux_services"]["hosts"]

    assert len(hosts) == 1
    assert hosts[0]["ssh_username"] == "pi-hole"


# --------------------------------------------------------------------
# "Nothing reached, nothing rendered"
# --------------------------------------------------------------------


def test_a_host_that_matches_no_username_is_absent():
    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, ssh_table={})

    observation = provider(runner).collect()
    assert observation["linux_services"]["hosts"] == []


def test_nmap_raising_yields_no_hosts_and_no_ssh_attempts():
    runner = FakeRunner(raise_on_nmap=True)

    observation = provider(runner).collect()

    assert observation["linux_services"]["hosts"] == []
    assert all(call[0] != "ssh" for call in runner.calls)


def test_nmap_non_zero_exit_yields_no_hosts():
    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, nmap_returncode=1)

    observation = provider(runner).collect()
    assert observation["linux_services"]["hosts"] == []


def test_a_down_host_in_nmap_output_is_never_tried():
    runner = FakeRunner(
        nmap_stdout="Host: 192.168.1.150 ()\tStatus: Down\n",
        ssh_table=full_table("192.168.1.150", "pi"),
    )

    observation = provider(runner).collect()

    assert observation["linux_services"]["hosts"] == []
    assert all(call[0] != "ssh" for call in runner.calls)


# --------------------------------------------------------------------
# Partial observation (cadrage decision, 2026-11-28): a missing signal
# never excludes the host, only that one field.
# --------------------------------------------------------------------


def test_a_host_with_no_package_manager_is_still_observed_without_a_version():
    ip, username = "192.168.1.40", "pi"
    table = full_table(ip, username)
    # dpkg and rpm both fail (255, no match in the table): no package
    # manager AIStack recognises on this host.

    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, ssh_table=table)

    observation = provider(runner).collect()
    mariadb = next(
        s for s in observation["linux_services"]["hosts"][0]["services"] if s["service"] == "mariadb"
    )

    assert "package_version" not in mariadb
    assert mariadb["unit_state"] == "active"


def test_rpm_is_tried_when_dpkg_fails():
    ip, username = "192.168.1.40", "pi"
    table = full_table(ip, username)
    table[(ip, username, "rpm -q --qf '%{VERSION}' mariadb-server 2>/dev/null")] = (0, "10.11.6\n")

    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, ssh_table=table)

    observation = provider(runner).collect()
    mariadb = next(
        s for s in observation["linux_services"]["hosts"][0]["services"] if s["service"] == "mariadb"
    )

    assert mariadb["package_version"] == "10.11.6"


def test_a_missing_config_file_resolves_to_none_not_an_error():
    ip, username = "192.168.1.40", "pi"
    table = full_table(ip, username)
    # `test -e ... && echo present` fails silently (the && short-circuits).

    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, ssh_table=table)

    observation = provider(runner).collect()
    mariadb = next(
        s for s in observation["linux_services"]["hosts"][0]["services"] if s["service"] == "mariadb"
    )

    assert mariadb["config_path"] is None


def test_an_inactive_unit_is_still_observed_as_such():
    ip, username = "192.168.1.40", "pi"
    table = full_table(ip, username)
    table[(ip, username, "systemctl is-active mariadb.service")] = (3, "inactive\n")

    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, ssh_table=table)

    observation = provider(runner).collect()
    mariadb = next(
        s for s in observation["linux_services"]["hosts"][0]["services"] if s["service"] == "mariadb"
    )

    # `systemctl is-active` exits non-zero for an inactive unit — the
    # provider's own SSH helper reads that as "no answer" (`None`), so
    # an inactive unit reads as `unknown`, not a crash and not `active`.
    assert mariadb["unit_state"] == "unknown"


def test_a_host_reached_only_through_ss_with_every_systemctl_call_failing_is_still_observed():
    """A host that answers `ss` but rejects every `systemctl is-active`
    (a minimal container image, say) is still observed, not excluded —
    `reached` is true from the port scan alone."""

    ip, username = "192.168.1.40", "pi"
    table = {(ip, username, "ss -tlnp"): (0, "LISTEN 0 151 *:3306 *:*\n")}

    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, ssh_table=table)

    observation = provider(runner).collect()
    hosts = observation["linux_services"]["hosts"]

    assert len(hosts) == 1
    mariadb = next(s for s in hosts[0]["services"] if s["service"] == "mariadb")
    assert mariadb["unit_state"] == "unknown"
    assert mariadb["listening_ports"] == [3306]


# --------------------------------------------------------------------
# Listening ports: filtered to each service's own expected ports
# --------------------------------------------------------------------


def test_listening_ports_are_filtered_per_service_not_shared():
    ip, username = "192.168.1.40", "pi"
    table = full_table(
        ip,
        username,
        ss_output=(
            "LISTEN 0 151 *:3306 *:*\n"
            "LISTEN 0 244 *:5432 *:*\n"
            "LISTEN 0 511 *:80 *:*\n"
        ),
    )

    runner = FakeRunner(nmap_stdout=NMAP_ONE_HOST_UP, ssh_table=table)

    observation = provider(runner).collect()
    services = {
        entry["service"]: entry for entry in observation["linux_services"]["hosts"][0]["services"]
    }

    assert services["mariadb"]["listening_ports"] == [3306]
    assert services["postgresql"]["listening_ports"] == [5432]
    assert services["apache"]["listening_ports"] == [80]
    # PHP-FPM's expected port (9000) is not in the fake `ss` output —
    # a unix-socket-only setup is still observed, just with no ports.
    assert services["php"]["listening_ports"] == []


# --------------------------------------------------------------------
# The local machine is never SSH'd into as if it were remote
# --------------------------------------------------------------------


def test_the_local_machines_own_ip_is_never_tried_over_ssh():
    runner = FakeRunner(
        nmap_stdout=NMAP_TWO_HOSTS_UP,
        ssh_table=full_table("192.168.1.10", "pi"),
    )

    observation = provider(runner).collect()
    hosts = observation["linux_services"]["hosts"]

    assert all(host["host"] != "192.168.1.10" for host in hosts)
    assert not any(
        call[0] == "ssh" and call[-2].endswith("@192.168.1.10") for call in runner.calls
    )


# --------------------------------------------------------------------
# Shape, credentials, and determinism
# --------------------------------------------------------------------


def test_the_observation_carries_provider_identity_and_cidr():
    runner = FakeRunner()
    observation = provider(runner).collect()

    assert observation["provider"]["id"] == "aistack.provider.linux_services"
    assert observation["linux_services"]["cidr"] == "192.168.1.0/24"
    assert "collected_at" in observation


def test_the_declared_ssh_key_path_is_passed_to_ssh():
    runner = FakeRunner(
        nmap_stdout=NMAP_ONE_HOST_UP,
        ssh_table=full_table("192.168.1.40", "pi"),
    )

    provider(runner).collect()

    ssh_calls = [call for call in runner.calls if call[0] == "ssh"]
    assert ssh_calls
    assert "/home/big-brother/.ssh/id_ed25519" in ssh_calls[0]
