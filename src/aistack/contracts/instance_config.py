from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

DEVELOPMENT = "development"
PRODUCTION = "production"
PHASES = (DEVELOPMENT, PRODUCTION)


@dataclass(frozen=True)
class InstanceConfig:
    """
    AIStack's own address on this deployment: the LAN host and the port
    of each of its web apps, declared in `instance_config.yml`, never
    discovered.

    All AIStack apps run on one host, so one `lan_hostname` serves every
    `service_ports` entry. The install path and third-party service links
    are not part of this contract.
    """

    lan_hostname: str
    service_ports: Mapping[str, int]
    # ADR-0016: `development` while AIStack is being set up, `production`
    # once in real use. A config that says nothing is in production.
    phase: str = "production"

    @property
    def in_development(self) -> bool:
        return self.phase == DEVELOPMENT

    def __post_init__(self) -> None:
        if self.phase not in PHASES:
            raise ValueError(f"an instance config's phase must be one of {', '.join(PHASES)}: {self.phase!r}")

        if not self.lan_hostname.strip():
            raise ValueError("an instance config names no LAN hostname")

        if not self.service_ports:
            raise ValueError("an instance config declares no service ports")

        for service, port in self.service_ports.items():
            if not service.strip():
                raise ValueError("an instance config names a nameless service")

            if not (0 < port < 65536):
                raise ValueError(
                    f"{service} declares a port out of range: {port}"
                )

    def service_url(self, service: str) -> str:
        """
        `http://<lan_hostname>:<port>` for `service`. Raises ValueError
        when no port is declared for it.
        """

        if service not in self.service_ports:
            known = ", ".join(sorted(self.service_ports)) or "(none)"
            raise ValueError(
                f"instance config declares no port for {service!r} — "
                f"known: {known}"
            )

        return f"http://{self.lan_hostname}:{self.service_ports[service]}"
