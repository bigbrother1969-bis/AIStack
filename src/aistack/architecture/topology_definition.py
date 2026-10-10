from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalNodeDefinition:
    """
    One piece of infrastructure AIStack cannot observe (registrar, DNS/CDN
    provider, internet box, email provider), as the user declares it.

    `role` is a short label; `description` is the fuller account.
    """

    name: str
    role: str
    description: str = ""


@dataclass(frozen=True)
class HardwareProfileDefinition:
    """
    One physical host's static inventory (CPU, RAM, GPU, storage, OS),
    gathered by hand, never derived from usage metrics.

    This is what exists, not how full or loaded it is; the health cockpit
    covers usage. `gpu` is optional.
    """

    name: str
    model: str
    role: str
    cpu: str
    ram: str
    storage: str
    os_name: str
    gpu: str | None = None


@dataclass(frozen=True)
class BeszelConnectionDefinition:
    """
    Where to reach Beszel, never the credentials themselves.

    `url` is public. `email_env`/`password_env` name the environment
    variables holding the read-only account's credentials.
    """

    url: str
    email_env: str
    password_env: str


@dataclass(frozen=True)
class InfrastructureTopologyDefinition:
    """
    What exists outside the services graph: external nodes, hardware
    profiles, and the Beszel connection for live readings.

    Every field may be empty or `None`; `render_html` renders only the
    sub-sections that have content.
    """

    external_nodes: tuple[ExternalNodeDefinition, ...] = ()
    hardware: tuple[HardwareProfileDefinition, ...] = ()
    beszel: BeszelConnectionDefinition | None = None
