from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkDiscoveryDefinition:
    """
    Where and how `aistack.cli.network_docker_discover` looks for Docker
    containers on the other hosts of the LAN.

    `cidr` is the LAN only, never Docker bridge or VPN overlay networks.
    `ssh_key_path_env` names the environment variable holding the private
    key's path, never the path itself. `ssh_usernames` is an ordered list,
    since different hosts use different accounts: each host is tried with
    every name in turn, the first that authenticates is used, and a host
    matching none is left out of the observation, not reported as an error.
    """

    cidr: str
    ssh_key_path_env: str
    ssh_usernames: tuple[str, ...] = ()
    ssh_timeout_seconds: float = 3.0
    # `cidr: auto`: `cidr` is the host's own LAN, read from its routes when
    # the file is loaded, and `auto` is what a save writes back.
    cidr_auto: bool = False


AUTO = "auto"
# What `auto` gives when the routes name no LAN: the host alone.
ALONE = "127.0.0.1/32"


def _hex_address(value: str) -> str:
    # /proc/net/route writes an IPv4 address as 8 hex digits, little-endian.
    raw = bytes.fromhex(value)
    return ".".join(str(byte) for byte in reversed(raw))


def discover_cidr(routes: str) -> str | None:
    """The host's LAN, from a `/proc/net/route` text: the directly
    connected network of the interface carrying the default route."""

    rows = [line.split() for line in routes.splitlines()[1:] if len(line.split()) >= 8]
    default = next((row[0] for row in rows if row[1] == "00000000" and row[7] == "00000000"), None)
    if default is None:
        return None
    for row in rows:
        interface, destination, gateway, mask = row[0], row[1], row[2], row[7]
        if interface == default and destination != "00000000" and gateway == "00000000" and mask != "00000000":
            bits = bin(int.from_bytes(bytes.fromhex(mask), "little")).count("1")
            return f"{_hex_address(destination)}/{bits}"
    return None


def read_routes() -> str:
    from pathlib import Path

    try:
        return Path("/proc/net/route").read_text(encoding="ascii")
    except OSError:
        return ""
