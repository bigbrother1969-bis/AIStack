from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from aistack.config import configured
from aistack.generators.network_docker import NetworkDockerObservationArtifactGenerator
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.network_discovery.yaml import load_network_discovery_yaml
from aistack.providers.network_docker import NetworkDockerDiscoveryProvider

DEFAULT_GENERATED_DIR = "reports/generated"

DEFAULT_DEFINITION = configured(
    Path(__file__).resolve().parents[1]
    / "network_discovery"
    / "definitions"
    / "network_discovery.yml"
)


class NetworkDockerDiscoverTask:
    """
    Scan the network for Docker hosts and write a separate JSON report
    (`network_docker.discover`, ADR-0027 § 10).

    The fifth chain the Runtime executes. Run on demand or by the vigil,
    never from `architecture.render`: a network scan with SSH attempts is
    an action, not a passive read. The request payload's `generated_dir`
    (default `DEFAULT_GENERATED_DIR`) says where the observation is
    written.

    **The SSH key path is read from the environment here, never carried
    by the request**: the Runtime keeps the request in its trace, and the
    path would be written to disk and kept for good. The variable's name
    is the one the governed definition declares (`ssh_key_path_env`).

    The provider is configured at use (CIDR, key, user names): it is
    built here, as `architecture.render` builds its own, and not asked
    of the Kernel (ADR-0027 § 4).

    Returns an Observation of plain values: where the report was written
    and how many hosts it found.
    """

    task_id = "network_docker.discover"
    task_name = "Network Docker discovery"

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = environ

    def execute(self, request: Request) -> Observation:
        environ = os.environ if self._environ is None else self._environ
        generated_dir = Path(request.payload.get("generated_dir", DEFAULT_GENERATED_DIR))

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
            output_path=generated_dir / "network-docker-observation.json",
        )

        return Observation(
            context=ObservationContext(
                request_id=request.request_id,
                component_type="task",
                component_id=self.task_id,
                operation="execute",
            ),
            data={
                "output_path": str(output_path),
                "hosts": len(observation.get("network_docker", {}).get("hosts", [])),
            },
        )
