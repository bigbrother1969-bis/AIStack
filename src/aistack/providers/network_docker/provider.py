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
    """
    Observe Docker containers on hosts other than the one this
    process runs on — `claude/PLAN-J11-CONSOLE-2026-09-11.md` §11,
    the gap `DockerProvider` itself already names as a known
    limitation (only ever the local `docker`/socket).

    **Two real actions, in sequence, both scoped and confirmed with
    the owner before this was written (`GOV-P-001`/`ARC-P-006`).**
    First, an `nmap` ping sweep of the owner's own declared LAN
    (never a wider range — see `NetworkDiscoveryDefinition.cidr`'s
    own docstring) finds which hosts are live right now. Second,
    every live host that is not this machine itself is tried, in
    order, against each declared SSH username with the declared
    key, running the exact same `docker ps -a --format '{{json .}}'`
    `DockerProvider.collect()` already runs locally — a host that
    authenticates against none of them, or that authenticates but
    has no Docker at all, is simply absent from the result
    (`ARC-P-012`: no container is asserted where none was actually
    observed), never an error and never a partial guess.

    **Never triggered automatically.** Decided with the owner
    2026-09-12: unlike `DockerProvider`/`ComposeProvider`/
    `BeszelProvider`, this collector is not wired into
    `architecture_render` — a network scan and a set of SSH
    connection attempts against the owner's own machines is an
    action, not a passive read, so it only runs when
    `aistack.cli.network_docker_discover` is invoked explicitly.

    **`run_command` is injectable, defaulting to `subprocess.run`.**
    Both `nmap` and `ssh` are external processes this class does not
    control the presence, version or behaviour of on a real host —
    every test in this heritage that reaches an external command
    this way (`DockerProvider`, `ComposeProvider`'s own
    `docker inspect`) stubs at that same boundary, never the
    daemon/network itself. Passing a fake here lets every test
    exercise the real parsing logic against canned `nmap`/`ssh`
    output, with no real subprocess ever spawned.
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
        """
        A ping sweep, not a port scan — `nmap -sn` never touches any
        port on a live host, it only asks "is anything there". Which
        hosts turn out to run Docker (or accept the declared SSH
        usernames at all) is answered afterwards, per host, by
        actually trying — decided with the owner 2026-09-12 in
        preference to pre-filtering by an open SSH port, so that a
        host running SSH on a non-standard port is not silently
        skipped.

        `-oG -` (grepable output, to stdout) rather than the default
        human-readable report: one `Host: <ip> (...)  Status: Up`
        line per live host, trivial to parse without depending on
        `nmap`'s XML output or a third-party parser.

        Absent `nmap`, a non-zero exit, or any other failure to run
        it at all reads as "no live hosts found" — the same
        tolerant-provider convention `ComposeProvider._read_depends_on`
        already holds for a compose file that cannot be read: nothing
        observed, nothing to report, never a raised exception from a
        collector this heritage otherwise never lets fail a whole
        run.
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
            f"ConnectTimeout={self._timeout_seconds}",
            f"{username}@{ip}",
            "docker ps -a --format {{json .}}",
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
        """
        This machine's own LAN address(es), so a host discovered by
        the scan is never also SSH'd into as if it were remote —
        `DockerProvider` already observes this machine directly and
        far more cheaply.

        A UDP "connect" to a non-routed address never sends a
        packet — it only asks the kernel which local interface
        would carry it — so this never touches the network itself,
        the same reasoning that makes it a standard, dependency-free
        way to find a host's own primary outbound address. Any
        failure (no network at all) leaves only the loopback address
        excluded, never raises.
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
