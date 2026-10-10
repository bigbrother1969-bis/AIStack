from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from aistack.network_discovery.definition import (
    ALONE,
    AUTO,
    NetworkDiscoveryDefinition,
    discover_cidr,
    read_routes,
)

_REQUIRED_FIELDS = ("cidr", "ssh_key_path_env")

_HEADER_COMMENT = """\
# AIStack — network Docker discovery
#
# Where AIStack looks for Docker containers on the other hosts of the
# local network, and how it authenticates to them. `ssh_usernames` is
# also written back by the Network discovery screen (local network
# only) when an administrator adds or removes a username there.
#
# `cidr`: `auto` reads the server's own LAN from its routes (the
# network of the interface carrying the default route); or a network
# written by hand, for instance 192.168.0.0/24 — never wider than the
# LAN.
#
# `ssh_key_path_env` names the environment variable that carries the
# path to an existing SSH private key — never the key or its path
# itself.
#
# `ssh_usernames` is tried, in order, against every host the scan
# finds; the first that authenticates is used.
"""

def load_network_discovery_yaml(path: Path) -> NetworkDiscoveryDefinition:
    """
    Load the network-discovery definition from YAML. `cidr: auto` is
    resolved from the host's routes. A missing `ssh_usernames` means an
    empty list: nothing to authenticate with yet.
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

    declared = str(data["cidr"]).strip()
    automatic = declared == AUTO
    cidr = (discover_cidr(read_routes()) or ALONE) if automatic else declared

    return NetworkDiscoveryDefinition(
        cidr=cidr,
        cidr_auto=automatic,
        ssh_key_path_env=data["ssh_key_path_env"],
        ssh_usernames=tuple(str(name) for name in ssh_usernames_data),
        ssh_timeout_seconds=float(data.get("ssh_timeout_seconds") or 3.0),
    )


def save_network_discovery_yaml(
    definition: NetworkDiscoveryDefinition, path: Path
) -> Path:
    """
    Save a network-discovery definition to YAML, the inverse of
    `load_network_discovery_yaml`.

    Every field is written, even though the screen changes only
    `ssh_usernames`. A static header comment is written first, because
    PyYAML drops comments.
    """

    path.parent.mkdir(parents=True, exist_ok=True)

    body = {
        "cidr": AUTO if definition.cidr_auto else definition.cidr,
        "ssh_key_path_env": definition.ssh_key_path_env,
        "ssh_timeout_seconds": definition.ssh_timeout_seconds,
        "ssh_usernames": list(definition.ssh_usernames),
    }

    with path.open("w", encoding="utf-8") as stream:
        stream.write(_HEADER_COMMENT)
        stream.write("\n")
        # `yaml.safe_dump` rather than hand-written lines, so values with
        # YAML-special characters are quoted and load back correctly.
        yaml.safe_dump(body, stream, sort_keys=False, allow_unicode=True)

    return path


def _require(data: dict[str, Any], fields: tuple[str, ...], label: str) -> None:
    missing = [field for field in fields if field not in data]

    if missing:
        raise ValueError(f"{label} is missing: {', '.join(missing)}")
