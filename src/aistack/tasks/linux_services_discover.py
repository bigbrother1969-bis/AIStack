from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path

from aistack.config import configured
from aistack.generators.linux_services import LinuxServicesObservationArtifactGenerator
from aistack.kernel.execution import Observation, ObservationContext, Request
from aistack.network_discovery.yaml import load_network_discovery_yaml
from aistack.providers.linux_services import LinuxServicesDiscoveryProvider

DEFAULT_GENERATED_DIR = "reports/generated"

DEFAULT_DEFINITION = configured(
    Path(__file__).resolve().parents[1]
    / "network_discovery"
    / "definitions"
    / "network_discovery.yml"
)


class LinuxServicesDiscoverTask:
    """
    Scan the network for the four target services outside Docker —
    MariaDB/MySQL, PostgreSQL, Apache, PHP — and write a separate JSON
    report (`linux_services.discover`, `ADR-0035`).

    Reuses `network_discovery.yml` exactly as `network_docker.discover`
    does — the same CIDR, the same declared SSH key and usernames, one
    scan feeding both collections (`ADR-0035`'s second correction: this
    is not `hosts.yml`, which is a separate, passive subsystem). Run on
    demand only, never from `architecture.render`: an SSH scan is an
    action, not a passive read. The request payload's `generated_dir`
    (default `DEFAULT_GENERATED_DIR`) says where the observation is
    written.

    **The SSH key path is read from the environment here, never carried
    by the request** — same reasoning as `NetworkDockerDiscoverTask`:
    the Runtime keeps the request in its trace, and the path would be
    written to disk and kept for good.

    The provider is configured at use (CIDR, key, user names): it is
    built here and not asked of the Kernel (ADR-0027 § 4).

    Returns an Observation of plain values: where the report was
    written and how many hosts it found.
    """

    task_id = "linux_services.discover"
    task_name = "Linux services discovery"

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._environ = environ

    def execute(self, request: Request) -> Observation:
        environ = os.environ if self._environ is None else self._environ
        generated_dir = Path(request.payload.get("generated_dir", DEFAULT_GENERATED_DIR))

        definition = load_network_discovery_yaml(DEFAULT_DEFINITION)
        ssh_key_path = environ.get(definition.ssh_key_path_env, "")

        observation = LinuxServicesDiscoveryProvider(
            cidr=definition.cidr,
            ssh_key_path=ssh_key_path,
            ssh_usernames=definition.ssh_usernames,
            timeout_seconds=definition.ssh_timeout_seconds,
        ).collect()

        output_path = LinuxServicesObservationArtifactGenerator().generate(
            observation=observation,
            output_path=generated_dir / "linux-services-observation.json",
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
                "hosts": len(observation.get("linux_services", {}).get("hosts", [])),
            },
        )
