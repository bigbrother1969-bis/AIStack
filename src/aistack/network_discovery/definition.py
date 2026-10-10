from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NetworkDiscoveryDefinition:
    """
    Where and how `aistack.cli.network_docker_discover` looks for
    Docker containers on hosts other than the one AIStack itself
    runs on — `claude/PLAN-J11-CONSOLE-2026-09-11.md` §11.

    **`cidr` is the owner's own LAN, never guessed.** Confirmed
    2026-09-12 from `ip -4 addr show`/`ip route` run on GIGABYTE
    (`enp2s0`, `192.168.1.10/24`, default route via
    `192.168.1.254`) — deliberately excludes GIGABYTE's own Docker
    bridge networks (`172.x`, `br-*`) and its Tailscale overlay
    (`100.100.221.30`), none of which are the LAN a remote homelab
    host sits on.

    **`ssh_key_path_env` names an environment variable, never a
    path itself** (`GOV-P-001`, same handling as
    `BeszelConnectionDefinition.email_env`/`password_env`) — the key
    file already exists on disk (GIGABYTE's own
    `~/.ssh/id_ed25519`), outside this repository; this dataclass
    only names where its real path is read from at run time.

    **`ssh_usernames` is a short, ordered, declared list — not a
    single username.** Confirmed 2026-09-12 by actually connecting:
    the Raspberry Pi's own SSH user is `pi`, the Pi-hole VM's is
    `pi-hole` — two different real accounts for two real hosts, so a
    single declared username would have missed one of them by
    design, not by oversight. Each discovered host is tried against
    every name in order; the first that authenticates is used, and a
    host that matches none is simply absent from the observation
    (`ARC-P-012` — no relationship is asserted where none was
    confirmed), never an error.
    """

    cidr: str
    ssh_key_path_env: str
    ssh_usernames: tuple[str, ...] = ()
    ssh_timeout_seconds: float = 3.0
    # `cidr: auto` (2.0.0-rc1, a new installation discovers its network):
    # `cidr` is then the host's own LAN, read from its routes when the
    # file is loaded, and `auto` is what a save writes back.
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
