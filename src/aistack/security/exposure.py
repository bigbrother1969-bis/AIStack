"""
What the host exposes, read and judged (ADR-0028 § 2, slice T1).

Two readings, both read-only and both made from where AIStack runs
(`network_mode: host`, so the container sees the host's sockets):

- the listening sockets, from `/proc/net/{tcp,tcp6,udp,udp6}`, with no
  external tool and no privilege;
- the ports Docker publishes, from `docker ps`, to name who owns a port.

The firewall is **not read**: the image holds neither `iptables` nor
`ufw`, and a reading made from a private network namespace would say
"no rule" about a host that has some. The assessment says so, in every
report, instead of guessing.
"""

from __future__ import annotations

import ipaddress
import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from aistack.security.definition import SecurityDefinition
from aistack.security.findings import FIX, INFORMATION, WATCH, Finding

PROC_NET = Path("/proc/net")
_TABLES = (("tcp", "tcp"), ("tcp6", "tcp"), ("udp", "udp"), ("udp6", "udp"))
# /proc/net/tcp: state 0A is LISTEN. /proc/net/udp: 07 is a bound socket
# with no peer, the nearest to "listening" a datagram socket has.
_LISTENING = {"tcp": "0A", "udp": "07"}

ALL = "all"
SPECIFIC = "specific"
LOOPBACK = "loopback"
_REACH = (LOOPBACK, SPECIFIC, ALL)

CommandRunner = Callable[..., "subprocess.CompletedProcess[str]"]


@dataclass(frozen=True)
class Listener:
    """A port something listens on: `bind` says how far it can be reached."""

    protocol: str
    port: int
    bind: str


@dataclass(frozen=True)
class Published:
    """A port Docker publishes for a container."""

    container: str
    protocol: str
    port: int
    bind: str


def _address(value: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    # The kernel writes each 4-byte word of an address in host (little-endian) order.
    try:
        raw = bytes.fromhex(value)
    except ValueError:
        return None

    words = b"".join(raw[i : i + 4][::-1] for i in range(0, len(raw), 4))

    try:
        if len(words) == 4:
            return ipaddress.IPv4Address(words)
        if len(words) == 16:
            return ipaddress.IPv6Address(words)
    except ValueError:
        return None
    return None


def _bind(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str:
    if address.is_unspecified:
        return ALL
    mapped = getattr(address, "ipv4_mapped", None)
    if address.is_loopback or (mapped is not None and mapped.is_loopback):
        return LOOPBACK
    return SPECIFIC


def parse_sockets(protocol: str, text: str) -> list[Listener]:
    """The listeners in one `/proc/net` table; a line it cannot read is skipped."""

    listeners: list[Listener] = []

    for line in text.splitlines()[1:]:
        fields = line.split()

        if len(fields) < 4 or fields[3] != _LISTENING[protocol]:
            continue

        host, _, port_hex = fields[1].rpartition(":")
        address = _address(host)

        try:
            port = int(port_hex, 16)
        except ValueError:
            continue

        if address is None or port == 0:
            continue

        listeners.append(Listener(protocol, port, _bind(address)))

    return listeners


def merge(listeners: list[Listener]) -> list[Listener]:
    """One listener per protocol and port, at the widest reach it has (IPv4 and IPv6 merge)."""

    widest: dict[tuple[str, int], str] = {}

    for item in listeners:
        key = (item.protocol, item.port)
        if key not in widest or _REACH.index(item.bind) > _REACH.index(widest[key]):
            widest[key] = item.bind

    return [Listener(protocol, port, bind) for (protocol, port), bind in sorted(widest.items())]


def read_listeners(proc_net: Path = PROC_NET) -> tuple[list[Listener], list[str]]:
    """The host's listeners and the tables that could not be read."""

    found: list[Listener] = []
    unread: list[str] = []

    for table, protocol in _TABLES:
        try:
            text = (proc_net / table).read_text(encoding="ascii", errors="replace")
        except OSError:
            unread.append(table)
            continue
        found.extend(parse_sockets(protocol, text))

    return merge(found), unread


def parse_published(containers: str) -> list[Published]:
    """The published ports in `docker ps --format '{{json .}}'` lines."""

    published: list[Published] = []

    for line in containers.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(entry, dict):
            continue

        name = str(entry.get("Names", "")).strip()

        for part in str(entry.get("Ports", "")).split(","):
            left, arrow, right = part.strip().partition("->")

            if not arrow:
                continue

            host, _, ports = left.rpartition(":")
            protocol = right.rpartition("/")[2] or "tcp"
            bind = host.strip("[]")
            reach = ALL if bind in ("", "0.0.0.0", "::") else LOOPBACK if bind.startswith("127.") or bind == "::1" else SPECIFIC
            first, _, last = ports.partition("-")

            try:
                low, high = int(first), int(last or first)
            except ValueError:
                continue

            for port in range(low, min(high, low + 1024) + 1):
                published.append(Published(name, protocol, port, reach))

    return published


def read_published(run_command: CommandRunner = subprocess.run) -> list[Published] | None:
    """The ports Docker publishes; None when `docker` cannot be asked."""

    try:
        result = run_command(
            ["docker", "ps", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    return parse_published(result.stdout)


def _name(listener: Listener, owners: dict[tuple[str, int], str]) -> str:
    owner = owners.get((listener.protocol, listener.port))
    return f"{listener.port}/{listener.protocol}" + (f" ({owner})" if owner else "")


def _listed(names: list[str], limit: int) -> tuple[str, ...]:
    if len(names) <= limit:
        return tuple(names)
    return (*names[:limit], f"and {len(names) - limit} more")


def assess(
    listeners: list[Listener],
    unread_tables: list[str],
    published: list[Published] | None,
    definition: SecurityDefinition,
) -> list[Finding]:
    """What the readings say, judged against the owner's declaration (ADR-0028 § 3)."""

    findings: list[Finding] = []
    owners = {
        (item.protocol, item.port): item.container
        for item in (published or [])
        if item.bind == ALL
    }

    if unread_tables:
        findings.append(
            Finding(
                "exposure.sockets_unreadable",
                WATCH,
                "Some of the host's socket tables could not be read",
                tuple(unread_tables),
                unknown="What listens in the tables that could not be read.",
            )
        )

    if published is None:
        findings.append(
            Finding(
                "exposure.docker_unreadable",
                WATCH,
                "Docker could not be asked which ports it publishes",
                unknown="Which container owns a port.",
            )
        )

    findings.append(
        Finding(
            "firewall.not_read",
            INFORMATION,
            "The firewall is not read from here",
            ("neither iptables nor ufw is available to this assessment",),
            unknown="Whether a port listening on every interface is actually reachable from outside the LAN.",
        )
    )

    wide = [item for item in listeners if item.bind == ALL]
    handled: set[tuple[str, int]] = set()

    for item in wide:
        if item.port in definition.declared_ports:
            handled.add((item.protocol, item.port))
            continue

        if item.port in definition.critical_ports:
            handled.add((item.protocol, item.port))
            findings.append(
                Finding(
                    f"exposure.critical.{item.protocol}.{item.port}",
                    FIX,
                    f"{definition.critical_ports[item.port]} listens on every interface",
                    (_name(item, owners),),
                    unknown="Whether a firewall stops it from being reached from outside.",
                )
            )
        elif item.port in definition.sensitive_ports:
            handled.add((item.protocol, item.port))
            findings.append(
                Finding(
                    f"exposure.sensitive.{item.protocol}.{item.port}",
                    WATCH,
                    f"{definition.sensitive_ports[item.port]} listens on every interface",
                    (_name(item, owners),),
                    unknown="Whether a firewall stops it from being reached from outside.",
                )
            )

    others = [_name(item, owners) for item in wide if (item.protocol, item.port) not in handled
              and item.port not in definition.declared_ports]

    if others:
        findings.append(
            Finding(
                "exposure.undeclared_on_all_interfaces",
                WATCH,
                f"{len(others)} port(s) listen on every interface and are not declared",
                _listed(others, definition.max_listed),
                unknown="What each one is for; declare the ones that are yours in security.yml.",
            )
        )

    listening = {item.port for item in listeners}
    missing = [f"{port} ({purpose})" if purpose else str(port)
               for port, purpose in sorted(definition.declared_ports.items()) if port not in listening]

    if missing:
        findings.append(
            Finding(
                "exposure.declared_not_listening",
                INFORMATION,
                f"{len(missing)} declared port(s) have nothing listening",
                _listed(missing, definition.max_listed),
                unknown="Whether the service is stopped on purpose.",
            )
        )

    return findings


def propose_declaration(
    listeners: list[Listener],
    published: list[Published] | None,
    definition: SecurityDefinition,
) -> str:
    """
    The `declared_ports` block that would silence what is listening today.

    A starting point for the owner to read, never applied: it states what
    is there now, not what is right. Sensitive and critical ports are left
    out on purpose, so they stay in the report until the owner declares
    them by hand. A port is named after the container that publishes it,
    `host` when no container does.
    """

    owners = {
        item.port: item.container
        for item in (published or [])
        if item.bind == ALL
    }
    ports = sorted(
        {
            item.port
            for item in listeners
            if item.bind == ALL
            and item.port not in definition.declared_ports
            and item.port not in definition.sensitive_ports
            and item.port not in definition.critical_ports
        }
    )

    if not ports:
        return "declared_ports: {}\n"

    lines = ["declared_ports:"]
    lines.extend(f"  {port}: {owners.get(port, 'host')}" for port in ports)
    return "\n".join(lines) + "\n"
