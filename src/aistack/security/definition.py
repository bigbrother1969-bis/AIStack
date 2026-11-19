from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SecurityDefinition:
    """
    What the owner declares about the host's exposure (ADR-0028 § 2).

    `declared_ports` are the ports the owner expects to find listening on
    every interface, with their purpose: a declared port is no longer
    reported. `sensitive_ports` are ports whose service should not be
    reachable from every network (a database, a file share, SSH): listening
    on every interface without being declared is a finding to watch.
    `critical_ports` are ports whose service gives control of the host to
    whoever reaches it (the Docker API): the same, as a finding to fix.
    `accepted` names, per kind of risk, the containers the owner accepts
    carrying it (a monitor with the Docker socket, say): they are counted,
    not reported. `max_listed` bounds how many names one finding carries.
    """

    declared_ports: dict[int, str] = field(default_factory=dict)
    sensitive_ports: dict[int, str] = field(default_factory=dict)
    critical_ports: dict[int, str] = field(default_factory=dict)
    accepted: dict[str, tuple[str, ...]] = field(default_factory=dict)
    max_listed: int = 20
