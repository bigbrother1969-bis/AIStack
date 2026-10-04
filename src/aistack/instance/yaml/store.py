from __future__ import annotations

from pathlib import Path

import yaml

from aistack.contracts.instance_config import InstanceConfig


def load_instance_config_yaml(path: Path) -> InstanceConfig:
    """
    Load AIStack's own declared instance configuration from YAML —
    same shape and error discipline as
    `load_network_discovery_yaml`/`load_console_links_yaml`: a
    missing key names which one and where, never a silent default for
    a fact this heritage has never observed for itself (R10).
    """

    with path.open("r", encoding="utf-8") as stream:
        try:
            data = yaml.safe_load(stream)
        except yaml.YAMLError as error:
            raise ValueError(
                f"instance config {path} is not valid YAML: {error}"
            ) from error

    if not isinstance(data, dict):
        raise ValueError(f"instance config must contain a mapping: {path}")

    if "lan_hostname" not in data:
        raise ValueError(f"instance config {path} is missing: lan_hostname")

    if "service_ports" not in data:
        raise ValueError(f"instance config {path} is missing: service_ports")

    ports = data["service_ports"]

    if not isinstance(ports, dict):
        raise ValueError(f"instance config {path}: service_ports must be a mapping")

    return InstanceConfig(
        lan_hostname=str(data["lan_hostname"]),
        service_ports={
            str(service): int(port) for service, port in ports.items()
        },
        # Optional: absent means production, the strict rules (ADR-0016).
        phase=str(data.get("phase", "production")),
    )
