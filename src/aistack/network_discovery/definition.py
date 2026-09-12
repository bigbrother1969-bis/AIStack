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
