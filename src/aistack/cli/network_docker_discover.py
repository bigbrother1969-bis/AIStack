from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from aistack.generators.network_docker import NetworkDockerObservationArtifactGenerator
from aistack.network_discovery.yaml import load_network_discovery_yaml
from aistack.providers.network_docker import NetworkDockerDiscoveryProvider

# Same convention as `DEFAULT_TOPOLOGY`/`DEFAULT_CATEGORIZATION` in
# `architecture_render.py` — a `Path(__file__).resolve()`-relative
# default, not `importlib.resources`.
DEFAULT_DEFINITION = (
    Path(__file__).resolve().parents[1]
    / "network_discovery"
    / "definitions"
    / "network_discovery.yml"
)


def main(environ: Mapping[str, str] | None = None) -> None:
    """
    `claude/PLAN-J11-CONSOLE-2026-09-11.md` §11: a network Docker
    discovery, run on demand — never wired into `architecture_render`
    (decided with the owner 2026-09-12: a network scan plus a set of
    SSH connection attempts is an action, not a passive read, so it
    only happens when this command is invoked explicitly).

    **A separate report, not (yet) integrated into
    `architecture.html`** — decided with the owner the same day. A
    service `service_categorization.yml` already declares (Nginx
    Proxy Manager, Vaultwarden, Vikunja...) that this run discovers
    actually running on the Raspberry Pi or the Pi-hole VM stays
    shown as "déclaré, non observé" there for now; wiring this
    observation into that status is future work, not this command's
    job.

    The real SSH key's path is read from `environ` (real
    `os.environ` by default, injectable for tests — the same
    convention `architecture_render.main` already uses for Beszel's
    own credentials) under the environment variable name
    `NetworkDiscoveryDefinition.ssh_key_path_env` names; never the
    path itself, which is never written into any governed file
    (`GOV-P-001`).
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
