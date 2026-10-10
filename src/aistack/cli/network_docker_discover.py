from __future__ import annotations

from aistack.config import configured

import os
from collections.abc import Mapping
from pathlib import Path

from aistack.generators.network_docker import NetworkDockerObservationArtifactGenerator
from aistack.network_discovery.yaml import load_network_discovery_yaml
from aistack.providers.network_docker import NetworkDockerDiscoveryProvider

DEFAULT_DEFINITION = (
    configured(Path(__file__).resolve().parents[1]
    / "network_discovery"
    / "definitions"
    / "network_discovery.yml")
)


def main(environ: Mapping[str, str] | None = None) -> None:
    """
    Scan the network for Docker hosts and write a separate JSON report.

    Run on demand only, never from `architecture_render`: a network scan
    with SSH attempts is an action, not a passive read. Its findings do
    not feed `architecture.html`. The SSH key path is read from `environ`
    under the variable `ssh_key_path_env` names, and never written to a file.
    """

    environ = os.environ if environ is None else environ

    definition = load_network_discovery_yaml(DEFAULT_DEFINITION)
    ssh_key_path = environ.get(definition.ssh_key_path_env, "")

    observation = NetworkDockerDiscoveryProvider(
        cidr=definition.cidr,
        ssh_key_path=ssh_key_path,
        ssh_usernames=definition.ssh_usernames,
        timeout_seconds=definition.ssh_timeout_seconds,
    ).collect()

    output_path = NetworkDockerObservationArtifactGenerator().generate(
        observation=observation,
        output_path=Path("reports/generated/network-docker-observation.json"),
    )

    print(f"Network Docker observation written to {output_path}")


if __name__ == "__main__":
    main()
