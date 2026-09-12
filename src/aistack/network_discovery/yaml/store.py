from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.network_discovery.definition import NetworkDiscoveryDefinition

_REQUIRED_FIELDS = ("cidr", "ssh_key_path_env")

_HEADER_COMMENT = """\
# AIStack — network Docker discovery (claude/PLAN-J11-CONSOLE-2026-09-11.md §11)
#
# Where AIStack looks for Docker containers on hosts other than the
# one it runs on itself, and how it authenticates to them. Read by
# `aistack.cli.network_docker_discover`; `ssh_usernames` is also
# written back by the network-discovery-ui screen (LAN-only,
# `network_discovery_ui/app.py`) when the owner adds or removes a
# candidate username there — everything else in this file stays
# hand-edited, the same discipline `infrastructure_topology.yml`
# already holds for facts nothing in this repository writes back.
#
# `cidr` is the owner's own LAN (confirmed 2026-09-12 from `ip -4
# addr show`/`ip route` on GIGABYTE), never a wider range. Widening
# it is a decision for the owner to make explicitly, not a default
# this file should ever silently carry.
#
# `ssh_key_path_env` names the environment variable that carries the
# real path to an existing SSH private key — never the key or its
# path itself (GOV-P-001).
#
# `ssh_usernames` is tried, in order, against every host the scan
# finds live; the first that authenticates is used. Confirmed
# 2026-09-12: the owner's own real hosts use different SSH usernames
# from one another (`pi` on the Raspberry Pi, `pi-hole` on the
# Pi-hole VM) — this is why a single username is not enough.
"""

def load_network_discovery_yaml(path: Path) -> NetworkDiscoveryDefinition:
    """
    Load the governed network-discovery definition from YAML.

    `ssh_usernames` defaults to an empty tuple when the key is
    absent — a freshly created file with no usernames declared yet
    is not malformed, it simply authenticates against nothing until
    the owner adds one (by hand, or through the network-discovery-ui
    screen).
    """

    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)

    if not isinstance(data, dict):
        raise ValueError(
            f"Network discovery definition must contain a mapping: {path}"
        )

    _require(data, _REQUIRED_FIELDS, f"Network discovery definition {path}")

    ssh_usernames_data = data.get("ssh_usernames") or []

    if not isinstance(ssh_usernames_data, list):
        raise ValueError(
            f"Network discovery definition {path}: ssh_usernames must be a list"
        )

    return NetworkDiscoveryDefinition(
        cidr=data["cidr"],
        ssh_key_path_env=data["ssh_key_path_env"],
        ssh_usernames=tuple(str(name) for name in ssh_usernames_data),
        ssh_timeout_seconds=float(data.get("ssh_timeout_seconds") or 3.0),
    )


def save_network_discovery_yaml(
    definition: NetworkDiscoveryDefinition, path: Path
) -> Path:
    """
    Save a governed network-discovery definition to YAML — the write
    side `network_discovery_ui/app.py`'s own add/remove-username
    action uses, symmetric to `load_network_discovery_yaml`.

    **Only `ssh_usernames` is ever expected to change through this
    function in practice** (the screen this exists for edits nothing
    else), but every field is written, the same "no silent partial
    file" discipline `save_resource_priority_yaml` already holds —
    a save that only wrote the one field it changed would produce a
    file whose shape depends on which function last touched it.

    Written with a static header comment, the same reasoning
    `save_resource_priority_yaml` documents: PyYAML's own dump
    carries no comments, so a single `yaml.safe_dump` over the whole
    mapping would discard this file's own documentation on every
    save from the UI.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    body = {
        "cidr": definition.cidr,
        "ssh_key_path_env": definition.ssh_key_path_env,
        "ssh_timeout_seconds": definition.ssh_timeout_seconds,
        "ssh_usernames": list(definition.ssh_usernames),
    }

    with path.open("w", encoding="utf-8") as stream:
        stream.write(_HEADER_COMMENT)
        stream.write("\n")
        # `yaml.safe_dump`, not hand-formatted lines: a username or
        # key-path-env name containing a character YAML treats
        # specially (a colon, a leading `-`) is quoted correctly
        # rather than producing a file this same module's own
        # `load_network_discovery_yaml` cannot parse back.
        yaml.safe_dump(body, stream, sort_keys=False, allow_unicode=True)

    return path


def _require(data: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
