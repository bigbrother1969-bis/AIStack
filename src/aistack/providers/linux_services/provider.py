from __future__ import annotations

import re
import socket
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

_DEFAULT_TIMEOUT_SECONDS = 3.0

CommandRunner = Callable[..., "subprocess.CompletedProcess[str]"]


class _TargetService:
    """One of the cadrage's four target services: its systemd unit, its
    `dpkg`/`rpm` package name, the config file to test for, and the TCP
    ports it is expected to listen on (a service bound to a unix socket
    only, such as PHP-FPM in many setups, is still observed — its
    `listening_ports` is simply empty, never an error)."""

    __slots__ = ("service", "unit", "package", "config_path", "expected_ports")

    def __init__(
        self, service: str, unit: str, package: str, config_path: str, expected_ports: tuple[int, ...]
    ) -> None:
        self.service = service
        self.unit = unit
        self.package = package
        self.config_path = config_path
        self.expected_ports = expected_ports


# The cadrage's four target services (`ADR-0035`): MariaDB/MySQL,
# PostgreSQL, Apache, PHP.
_TARGET_SERVICES: tuple[_TargetService, ...] = (
    _TargetService(
        "mariadb", "mariadb.service", "mariadb-server",
        "/etc/mysql/mariadb.conf.d/50-server.cnf", (3306,),
    ),
    _TargetService(
        "postgresql", "postgresql.service", "postgresql",
        "/etc/postgresql/*/main/postgresql.conf", (5432,),
    ),
    _TargetService(
        "apache", "apache2.service", "apache2",
        "/etc/apache2/apache2.conf", (80, 443),
    ),
    _TargetService(
        "php", "php-fpm.service", "php",
        "/etc/php/*/fpm/php.ini", (9000,),
    ),
)

_SS_PORT_PATTERN = re.compile(r":(\d+)\s")


class LinuxServicesDiscoveryProvider:
    """Observe four Linux services outside Docker, on every host the
    network-discovery scan reaches (`ADR-0035`).

    Follows `NetworkDockerDiscoveryProvider`'s shape exactly: the same
    CIDR sweep, the same declared SSH key and usernames
    (`network_discovery.yml`, not `hosts.yml` — see `ADR-0035`'s second
    correction), so one scan feeds both collections.

    For each live host that authenticates, four signals are read per
    target service — `systemctl is-active` for the unit state,
    `dpkg -s`/`rpm -q` (whichever the host answers to) for the package
    version, one host-wide `ss -tlnp` filtered to the service's own
    expected ports for `listening_ports`, and a plain existence test
    for the config file. A host missing a signal (no package manager,
    say, or a service bound to a unix socket only) is still observed
    for the others — never excluded (cadrage decision, 2026-11-28).

    An action, not a passive read: runs only from
    `aistack.cli.linux_services_discover`. `run_command` (default
    `subprocess.run`) is injectable for tests, exactly as for Docker.
    """

    provider_id = "aistack.provider.linux_services"
    provider_name = "Linux Services Discovery Provider"

    def __init__(
        self,
        cidr: str,
        ssh_key_path: str,
        ssh_usernames: tuple[str, ...],
        timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
        run_command: CommandRunner = subprocess.run,
        local_ips: frozenset[str] | None = None,
    ) -> None:
        self._cidr = cidr
        self._ssh_key_path = ssh_key_path
        self._ssh_usernames = tuple(ssh_usernames)
        self._timeout_seconds = timeout_seconds
        self._run_command = run_command
        self._local_ips_override = local_ips

    def collect(self) -> dict[str, Any]:
        live_hosts = self._discover_live_hosts()
        local_ips = (
            self._local_ips_override
            if self._local_ips_override is not None
            else self._detect_local_ips()
        )

        hosts: list[dict[str, Any]] = []

        for ip in live_hosts:
            if ip in local_ips:
                continue

            observed = self._observe_host(ip)

            if observed is not None:
                hosts.append(observed)

        hosts.sort(key=lambda entry: entry["host"])

        return {
            "provider": {
                "id": self.provider_id,
                "name": self.provider_name,
            },
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "linux_services": {
                "cidr": self._cidr,
                "hosts": hosts,
            },
        }

    def _discover_live_hosts(self) -> list[str]:
        """Identical to `NetworkDockerDiscoveryProvider`'s own sweep —
        same `nmap -sn` ping sweep, same declared CIDR."""

        try:
            result = self._run_command(
                ["nmap", "-sn", "-oG", "-", self._cidr],
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds * 50,
            )
        except (OSError, subprocess.TimeoutExpired):
            return []

        if result.returncode != 0:
            return []

        hosts: list[str] = []

        for line in result.stdout.splitlines():
            if not line.startswith("Host: "):
                continue

            if "Status: Up" not in line:
                continue

            fields = line.split()

            if len(fields) >= 2:
                hosts.append(fields[1])

        return hosts

    def _observe_host(self, ip: str) -> dict[str, Any] | None:
        for username in self._ssh_usernames:
            services = self._try_ssh_services(ip, username)

            if services is not None:
                return {
                    "host": ip,
                    "ssh_username": username,
                    "services": services,
                }

        return None

    def _try_ssh_services(
        self, ip: str, username: str
    ) -> list[dict[str, Any]] | None:
        """`None` means this username never authenticated at all (the
        host is tried with the next one, exactly like Docker). Once at
        least one command answers, every target service is reported,
        partially where a signal is unavailable."""

        listening_ports = self._listening_ports(ip, username)
        reached = listening_ports is not None
        services: list[dict[str, Any]] = []

        for target in _TARGET_SERVICES:
            unit_state = self._ssh_run(ip, username, f"systemctl is-active {target.unit}")

            if unit_state is not None:
                reached = True

            observed_at = datetime.now(timezone.utc).isoformat()

            entry: dict[str, Any] = {
                "service": target.service,
                "unit_state": (unit_state or "unknown").strip(),
                "listening_ports": sorted(
                    port for port in (listening_ports or []) if port in target.expected_ports
                ),
                "observed_at": observed_at,
            }

            package_version = self._package_version(ip, username, target.package)

            if package_version is not None:
                entry["package_version"] = package_version

            config_present = self._ssh_run(
                ip, username, f"test -e {target.config_path} && echo present"
            )
            entry["config_path"] = (
                target.config_path if (config_present or "").strip() == "present" else None
            )

            services.append(entry)

        return services if reached else None

    def _listening_ports(self, ip: str, username: str) -> list[int] | None:
        output = self._ssh_run(ip, username, "ss -tlnp")

        if output is None:
            return None

        return [int(match.group(1)) for match in _SS_PORT_PATTERN.finditer(output)]

    def _package_version(self, ip: str, username: str, package: str) -> str | None:
        dpkg = self._ssh_run(
            ip, username, f"dpkg-query -W -f='${{Version}}' {package} 2>/dev/null"
        )

        if dpkg:
            return dpkg.strip()

        rpm = self._ssh_run(ip, username, f"rpm -q --qf '%{{VERSION}}' {package} 2>/dev/null")

        if rpm:
            return rpm.strip()

        return None

    def _ssh_run(self, ip: str, username: str, remote_command: str) -> str | None:
        command = [
            "ssh",
            "-i",
            self._ssh_key_path,
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={round(self._timeout_seconds)}",
            f"{username}@{ip}",
            remote_command,
        ]

        try:
            result = self._run_command(command, capture_output=True, text=True)
        except OSError:
            return None

        if result.returncode != 0:
            return None

        return result.stdout

    def _detect_local_ips(self) -> frozenset[str]:
        """Identical to `NetworkDockerDiscoveryProvider`'s own
        detection, so this machine is never SSH'd into as a remote
        host."""

        local_ips = {"127.0.0.1"}

        try:
            probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            try:
                probe.connect(("10.255.255.255", 1))
                local_ips.add(probe.getsockname()[0])
            finally:
                probe.close()
        except OSError:
            pass

        return frozenset(local_ips)
