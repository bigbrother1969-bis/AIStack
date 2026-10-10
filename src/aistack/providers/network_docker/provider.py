from __future__ import annotations

import json
import socket
import subprocess
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

_DEFAULT_TIMEOUT_SECONDS = 3.0

CommandRunner = Callable[..., "subprocess.CompletedProcess[str]"]


class NetworkDockerDiscoveryProvider:
    """Observe Docker containers on other hosts of the declared LAN.

    An `nmap` ping sweep of the declared CIDR finds live hosts; each one
    that is not this machine is tried with each declared SSH username and
    key, running `docker ps -a --format '{{json .}}'`. A host that accepts
    no user or has no Docker is absent from the result, not an error.

    This is an action, not a passive read, so it runs only from
    `aistack.cli.network_docker_discover`. `run_command` (default
    `subprocess.run`) is injectable for tests.
    """

    provider_id = "aistack.provider.network_docker"
    provider_name = "Network Docker Discovery Provider"

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
            "network_docker": {
                "cidr": self._cidr,
                "hosts": hosts,
            },
        }

    def _discover_live_hosts(self) -> list[str]:
        """Live hosts from an `nmap -sn` ping sweep (no port scan).

        Not pre-filtered on port 22, so SSH on a non-standard port is still
        tried. Parses grepable output (`-oG -`). Any failure to run `nmap`
        returns `[]`.
        """

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
            containers = self._try_ssh_docker_ps(ip, username)

            if containers is not None:
                return {
                    "host": ip,
                    "ssh_username": username,
                    "containers": containers,
                }

        return None

    def _try_ssh_docker_ps(
        self, ip: str, username: str
    ) -> list[Any] | None:
        command = [
            "ssh",
            "-i",
            self._ssh_key_path,
            "-o",
            "BatchMode=yes",
            "-o",
            # ssh's ConnectTimeout only accepts whole seconds ("3.0" is
            # rejected as an invalid time value).
            f"ConnectTimeout={round(self._timeout_seconds)}",
            f"{username}@{ip}",
            "docker ps -a --format '{{json .}}'",
        ]

        try:
            result = self._run_command(
                command, capture_output=True, text=True
            )
        except OSError:
            return None

        if result.returncode != 0:
            return None

        containers: list[Any] = []

        for line in result.stdout.splitlines():
            if not line.strip():
                continue

            try:
                containers.append(json.loads(line))
            except json.JSONDecodeError:
                continue

        return containers

    def _detect_local_ips(self) -> frozenset[str]:
        """This machine's addresses, so it is not SSH'd into as a remote host.

        A UDP `connect` sends no packet; it only asks the kernel which local
        address would be used. On failure only loopback is returned.
        """

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
